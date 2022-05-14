from datetime import datetime

import attrs


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
