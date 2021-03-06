from datetime import datetime

import attrs

from ..db import attrs_model


@attrs_model(index=["!id", "room", "ts", "username", "flags", "deleted", "deleted_ts"])
@attrs.define
class Message:
    room: str
    id: str
    ts: datetime
    emblem: str
    username: str
    content: str
    flags: int = 0
    deleted: bool = False
    deleted_ts: datetime | None = None
