from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from backend import services


def test_default_clock_uses_jakarta_when_device_timezone_is_utc(monkeypatch):
    device_instant = datetime(2026, 9, 25, 1, 0, tzinfo=timezone.utc)
    requested_zones = []

    class SimulatedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            requested_zones.append(tz)
            instant = (
                device_instant.replace(tzinfo=None)
                if tz is None
                else device_instant.astimezone(tz)
            )
            return cls(
                instant.year,
                instant.month,
                instant.day,
                instant.hour,
                instant.minute,
                instant.second,
                instant.microsecond,
                tzinfo=instant.tzinfo,
            )

    monkeypatch.setattr(services, "datetime", SimulatedDateTime)

    assert services._now() == datetime(2026, 9, 25, 8, 0)
    assert requested_zones == [ZoneInfo("Asia/Jakarta")]
