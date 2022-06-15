from datetime import datetime
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
SERVER_TIME = ZoneInfo("America/Chicago")


def now() -> datetime:
    return datetime.now(tz=UTC)


def server_now() -> datetime:
    return datetime.now(tz=SERVER_TIME)
