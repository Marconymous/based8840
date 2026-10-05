"""`based8840` command line: parses arguments and runs the chosen command."""

import argparse
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, NoReturn, override

from rich.console import Console
from rich.text import Text

from based8840.errors import Based8840Error
from based8840.explain import explain_rule, list_rules
from based8840.fix import fix_project
from based8840.init import init_project
from based8840.project import find_project_dir
from based8840.report import print_path
from based8840.steps import ruff_format
from based8840.steps.command import CommandOutput, run_command
from based8840.verify import OUTPUT_FORMATS, VerifyOptions, verify_project

ERROR_TAIL_LINES: Final = 40
USAGE_ERROR_EXIT_CODE: Final = 2


class Arguments(argparse.Namespace):
    command: str
    project_dir: Path
    is_full: bool
    atlas_env: str
    changed_base: str
    output: str
    is_forced: bool
    code: str


@dataclass(frozen=True, slots=True)
class Parsers:
    root: argparse.ArgumentParser
    commands: Mapping[str, argparse.ArgumentParser]


class UsageParser(argparse.ArgumentParser):
    """Prints the full help, not only the one-line usage, before a usage error."""

    @override
    def error(self, message: str) -> NoReturn:
        self.print_help(sys.stderr)
        self.exit(USAGE_ERROR_EXIT_CODE, f"\n{self.prog}: error: {message}\n")


def main() -> None:
    arguments: Arguments = parse_arguments(sys.argv[1:])
    # JSON goes to stdout, so everything rich prints moves to stderr.
    console: Console = Console(stderr=getattr(arguments, "output", "") == "json")
    try:
        exit_code: int = run(arguments, console=console)
    except Based8840Error as error:
        console.print(Text(str(error), style="bold red"))
        sys.exit(USAGE_ERROR_EXIT_CODE)
    sys.exit(exit_code)


def parse_arguments(argv: Sequence[str]) -> Arguments:
    parsers: Parsers = _build_parsers()
    if not argv:
        parsers.root.error("no command given")
    # parse_known_args so leftovers are reported with the command's help, not the root's.
    arguments, extras = parsers.root.parse_known_args(argv, namespace=Arguments())
    command_parser: argparse.ArgumentParser = parsers.commands[arguments.command]
    if extras:
        command_parser.error(f"unrecognized arguments: {' '.join(extras)}")
    if getattr(arguments, "atlas_env", "") and not arguments.is_full:
        command_parser.error("--atlas-env needs --full (the Atlas check is opt-in, like layers)")
    return arguments


def run(arguments: Arguments, *, console: Console) -> int:
    if arguments.command == "explain":
        return explain_rule(arguments.code, console=console)
    if arguments.command == "rules":
        return list_rules(console=console)
    if arguments.command == "init":
        target_dir: Path = arguments.project_dir.resolve()
        print_path(console, command=arguments.command, project_dir=target_dir)
        return init_project(target_dir, is_forced=arguments.is_forced, console=console)
    project_dir: Path = find_project_dir(arguments.project_dir.resolve())
    print_path(console, command=arguments.command, project_dir=project_dir)
    if arguments.command == "format":
        return format_project(project_dir, console=console)
    if arguments.command == "fix":
        return fix_project(project_dir, console=console)
    options: VerifyOptions = VerifyOptions(
        is_full=arguments.is_full,
        atlas_env=arguments.atlas_env,
        changed_base=arguments.changed_base,
        output=arguments.output,
    )
    return verify_project(project_dir, options=options, console=console)


def format_project(project_dir: Path, *, console: Console) -> int:
    output: CommandOutput = run_command(ruff_format.FORMAT_COMMAND, cwd=project_dir)
    console.print(Text(output.tail(lines=ERROR_TAIL_LINES)))
    return output.exit_code


def _build_parsers() -> Parsers:
    parser: UsageParser = UsageParser(
        prog="based8840", description="Deterministic checks for the AGENTS.md rules."
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, metavar="COMMAND", parser_class=UsageParser
    )
    verify_parser: argparse.ArgumentParser = subparsers.add_parser(
        "verify", help="run every check, change nothing"
    )
    _add_verify_arguments(verify_parser)
    format_parser: argparse.ArgumentParser = subparsers.add_parser(
        "format", help="format every file with ruff format"
    )
    _add_project_dir(format_parser)
    fix_parser: argparse.ArgumentParser = subparsers.add_parser(
        "fix", help="ruff check --fix, ruff format, report what is left"
    )
    _add_project_dir(fix_parser)
    init_parser: argparse.ArgumentParser = subparsers.add_parser(
        "init", help="copy the agent files into a project and merge the tool config"
    )
    _ = init_parser.add_argument(
        "project_dir",
        nargs="?",
        type=Path,
        default=Path(),
        help="project directory with a pyproject.toml (default: current directory)",
    )
    _ = init_parser.add_argument(
        "--force", dest="is_forced", action="store_true", help="overwrite existing files"
    )
    explain_parser: argparse.ArgumentParser = subparsers.add_parser(
        "explain", help="why a rule exists, with a bad and a good example"
    )
    _ = explain_parser.add_argument("code", help="rule code, e.g. BC008 or PLR1702")
    rules_parser: argparse.ArgumentParser = subparsers.add_parser(
        "rules", help="list every rule and its AGENTS.md section"
    )
    return Parsers(
        root=parser,
        commands={
            "verify": verify_parser,
            "format": format_parser,
            "fix": fix_parser,
            "init": init_parser,
            "explain": explain_parser,
            "rules": rules_parser,
        },
    )


def _add_verify_arguments(parser: argparse.ArgumentParser) -> None:
    _add_project_dir(parser)
    _ = parser.add_argument(
        "-f", "--full", dest="is_full", action="store_true", help="also run opt-in checks"
    )
    _ = parser.add_argument(
        "--atlas-env",
        default="",
        metavar="ENV",
        help="with --full: run `atlas migrate validate --env ENV` (needed when atlas.hcl exists)",
    )
    _ = parser.add_argument(
        "--changed",
        dest="changed_base",
        default="",
        metavar="BRANCH",
        help="only report findings in files changed against BRANCH",
    )
    _ = parser.add_argument(
        "--output",
        choices=OUTPUT_FORMATS,
        default="text",
        help="github: also print Actions annotations; json: JSON on stdout (default: text)",
    )


def _add_project_dir(parser: argparse.ArgumentParser) -> None:
    _ = parser.add_argument(
        "project_dir",
        nargs="?",
        type=Path,
        default=Path(),
        help="project directory or any directory inside it (default: current directory)",
    )
