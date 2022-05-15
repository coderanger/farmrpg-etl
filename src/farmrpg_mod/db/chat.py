import sqlite3

import asyncpg
import structlog

from ..db import objects
from ..events import EVENTS
from ..models.chat import Message

log = structlog.stdlib.get_logger(mod="db.chat")


@EVENTS.on("chat")
async def on_chat(msg: Message):
    try:
        await objects(Message).create(msg)
    # TODO This should be a SQLAlchemy error once I ditch databases/orm.
    except (sqlite3.IntegrityError, asyncpg.exceptions.UniqueViolationError):
        pass  # Duplicate message, this is fine.


@EVENTS.on("flags")
async def on_flag(msg: Message):
    await objects(Message).filter(
        room=msg.room, username=msg.username, ts=msg.ts
    ).update(flags=msg.flags)
