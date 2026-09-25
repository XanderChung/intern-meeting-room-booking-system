from datetime import datetime, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from backend import services


def test_default_clock_uses_jakarta_when_device_timezone_is_utc(monkeypatch):
    device_instant = datetime(2026, 9, 25, 1, 0, tzinfo=timezone.utc)

    def simulated_system_clock(tz=None):
        if tz is None:
            return device_instant.replace(tzinfo=None)
        return device_instant.astimezone(tz)

    datetime_source = Mock()
    datetime_source.now.side_effect = simulated_system_clock
    monkeypatch.setattr(services, "datetime", datetime_source)

    assert services._now() == datetime(2026, 9, 25, 8, 0)
    datetime_source.now.assert_called_once_with(ZoneInfo("Asia/Jakarta"))
