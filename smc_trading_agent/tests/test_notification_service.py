"""
Component-focused tests for NotificationService using injected HTTP session
instead of patching aiohttp internals.
"""

import pytest

from ..risk_manager.notification_service import (
    NotificationService,
    NotificationChannel,
    NotificationPriority,
)


class MockResponse:
    def __init__(self, status: int, text: str = ""):
        self.status = status
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self):
        return self._text


class MockSession:
    """Minimal aiohttp-like session that returns status based on URL substring map."""

    def __init__(self, route_status_map: dict[str, int] | None = None, default_status: int = 200):
        self.route_status_map = route_status_map or {}
        self.default_status = default_status

    def post(self, url: str, *_, **__):
        for key, status in self.route_status_map.items():
            if key in url:
                return MockResponse(status)
        return MockResponse(self.default_status)


class TestNotificationService:
    """Test notification service functionality."""

    @pytest.mark.asyncio
    async def test_email_notification(self, mock_config):
        # Configure SendGrid path and inject mock session
        session = MockSession({"sendgrid.com": 202})
        service = NotificationService(mock_config['notifications'], http_session=session)
        service.email_config['sendgrid_api_key'] = 'test-key'

        result = await service.send_alert(
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.HIGH,
            subject="Test Alert",
            message="Test message",
            recipients=["test@example.com"]
        )

        assert result.success is True
        assert result.channel == NotificationChannel.EMAIL

    @pytest.mark.asyncio
    async def test_slack_notification(self, mock_config):
        # Configure Slack webhook and inject mock session
        session = MockSession({"hooks.slack.com": 200})
        service = NotificationService(mock_config['notifications'], http_session=session)
        service.slack_config['webhook_url'] = 'https://hooks.slack.com/services/T000/B000/XXX'

        result = await service.send_alert(
            channel=NotificationChannel.SLACK,
            priority=NotificationPriority.CRITICAL,
            subject="Test Alert",
            message="Test message",
            recipients=["#alerts"]
        )

        assert result.success is True
        assert result.channel == NotificationChannel.SLACK

    @pytest.mark.asyncio
    async def test_multi_channel_notification(self, mock_config):
        # Map both endpoints to their expected success statuses
        session = MockSession({
            "sendgrid.com": 202,
            "hooks.slack.com": 200,
        })
        service = NotificationService(mock_config['notifications'], http_session=session)
        service.email_config['sendgrid_api_key'] = 'test-key'
        service.slack_config['webhook_url'] = 'https://hooks.slack.com/services/T000/B000/XXX'

        results = await service.send_multi_channel_alert(
            channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
            priority=NotificationPriority.HIGH,
            subject="Test Alert",
            message="Test message",
            recipients={
                NotificationChannel.EMAIL: ["test@example.com"],
                NotificationChannel.SLACK: ["#alerts"]
            }
        )

        assert len(results) == 2
        for result in results:
            assert result.success is True


