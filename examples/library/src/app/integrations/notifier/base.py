from typing import Protocol

from app.models.domain.notification import Notification


class Notifier(Protocol):
    """Sends a notification to a person. Implementations live in impl/, one per file."""

    async def send(self, notification: Notification) -> None: ...
