from collections import defaultdict

import cattrs
import structlog
from google.cloud import firestore

from ..events import EVENTS
from ..models.chat import Message

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


@EVENTS.on("chat")
async def on_chat(msg: Message):
    data = cattrs.unstructure(msg)
    # We don't want to touch the flags count here.
    del data["flags"]
    # If the message isn't deleted, don't touch the deletion TS so it's preserved.
    if not msg.deleted:
        del data["deleted_ts"]
    doc_ref = rooms_col.document(msg.room).collection("chats").document(msg.id)
    await doc_ref.set(data, merge=True)
    id_map[msg.room][f"{msg.ts}|{msg.username}"] = msg.id


@EVENTS.on("flags")
async def on_flag(msg: Message):
    msg_id = id_map[msg.room].get(f"{msg.ts}|{msg.username}")
    if msg_id is not None:
        doc_ref = rooms_col.document(msg.room).collection("chats").document(msg_id)
        log.debug("Writing flags", msg_id=msg_id, flags=msg.flags)
        await doc_ref.set({"flags": msg.flags}, merge=True)
    else:
        log.warn(
            "Unable to find message ID for flags",
            room=msg.room,
            username=msg.username,
            ts=msg.ts,
        )
