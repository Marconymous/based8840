"""Notifier that writes notifications to the log."""

import logging
from typing import Final

from app.models.domain.notification import Notification

logger: Final = logging.getLogger(__name__)


class LogNotifier:
    """Writes notifications to the application log. Handy for production smoke tests."""

    async def send(self, notification: Notification) -> None:
        logger.info("notification to=%s subject=%s", notification.recipient, notification.subject)
