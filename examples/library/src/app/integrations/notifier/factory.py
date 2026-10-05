from app.core.settings import NotifierSettings
from app.integrations.notifier.base import Notifier
from app.integrations.notifier.impl.file import FileNotifier
from app.integrations.notifier.impl.log import LogNotifier


def create_notifier(settings: NotifierSettings) -> Notifier:
    match settings.kind:
        case "log":
            return LogNotifier()
        case "file":
            return FileNotifier(settings.file_path)
