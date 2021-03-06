from datetime import datetime

import attrs

from ..db import attrs_model


@attrs_model(
    index=["!id", "!firebase_uid"], primary_key="id", primary_key_writable=True
)
@attrs.define
class User:
    id: int
    firebase_uid: str | None = None


@attrs_model(index=["username"])
@attrs.define
class UserSnapshot:
    user: User
    ts: datetime
    username: str
    is_farmhand: bool = False
    is_ranger: bool = False


def get_custom_claims(snap: UserSnapshot):
    claims = {"username": snap.username}
    if snap.is_farmhand:
        claims["role"] = "farmhand"
    if snap.is_ranger:
        claims["role"] = "ranger"
    return claims
