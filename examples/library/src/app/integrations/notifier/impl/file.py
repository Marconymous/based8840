import asyncio
from pathlib import Path

from app.models.domain.notification import Notification


class FileNotifier:
    """Appends notifications as JSON lines to a local file (stand-in for an e-mail provider)."""

    def __init__(self, path: Path) -> None:
        self._path: Path = path

    async def send(self, notification: Notification) -> None:
        # File I/O blocks; run it in a worker thread so the event loop stays free.
        await asyncio.to_thread(self._append, notification.model_dump_json())

    def _append(self, line: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as file:
            _ = file.write(f"{line}\n")
