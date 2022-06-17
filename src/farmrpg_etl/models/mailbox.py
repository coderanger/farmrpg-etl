from datetime import datetime

import attrs


@attrs.define
class Mail:
    id: int
    username: str
    ts: datetime
    subject: str
    content: str
