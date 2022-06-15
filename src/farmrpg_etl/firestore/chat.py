import re
from collections import defaultdict

import cattrs
import structlog
from google.cloud import firestore

from ..events import EVENTS
from ..models.chat import Message

MENTION_RE = re.compile(r"@([^:\s]+(?:[^:]{0,29}?[^:\s](?=:))?)")

db = firestore.AsyncClient(project="farmrpg-mod")
rooms_col = db.collection("rooms")


log = structlog.stdlib.get_logger(mod="firestore.chat")


class MessageIDCache(dict[str, str]):
    def __init__(self, max_size: int):
        super().__init__()
        self.__max_size = max_size

    def __setitem__(self, key: str, value: str) -> None:
        super().__setitem__(key, value)
        if len(self) > self.__max_size:
            oldest_key = next(iter(self.keys()))
            del self[oldest_key]


# A cache used to mapping message IDs on flags because it's not (yet) included.
id_map = defaultdict(lambda: MessageIDCache(110))


# A set of all existing room docs to be used to avoid extraneous writes.
room_docs: set[str] = set()


@EVENTS.on("startup")
async def on_startup():
    docs = rooms_col.stream()  # type: ignore stream() has a mission Optional[]
    async for doc in docs:
        room_docs.add(doc.id)
    log.info("Found room docs", rooms=list(room_docs))


@EVENTS.on("chat")
async def on_chat(msg: Message):
    data = cattrs.unstructure(msg)
    # We don't want to touch the flags count here.
    del data["flags"]
    # If the message isn't deleted, don't touch the deletion TS so it's preserved.
    if not msg.deleted:
        del data["deleted_ts"]
    # Find any mentions so we can query on those.
    data["mentions"] = MENTION_RE.findall(msg.content)
    doc_ref = rooms_col.document(msg.room).collection("chats").document(msg.id)
    await doc_ref.set(data, merge=True)
    id_map[msg.room][f"{msg.ts}|{msg.username}"] = msg.id
    # Create the room doc if needed.
    if msg.room not in room_docs:
        room_dof_ref = rooms_col.document(msg.room)
        await room_dof_ref.set({"id": msg.room})  # type: ignore another bad Optional[]
        room_docs.add(msg.room)


@EVENTS.on("flags")
async def on_flag(msg: Message):
    msg_id = id_map[msg.room].get(f"{msg.ts}|{msg.username}")
    if msg_id is not None:
        doc_ref = (
            rooms_col.document(msg.room)
            .collection("chats")
            .document(msg_id)
            .collection("mod")
            .document("mod")
        )
        log.debug("Writing flags", msg_id=msg_id, flags=msg.flags)
        await doc_ref.set({"flags": msg.flags}, merge=True)
    else:
        log.warn(
            "Unable to find message ID for flags",
            room=msg.room,
            username=msg.username,
            ts=msg.ts,
        )
