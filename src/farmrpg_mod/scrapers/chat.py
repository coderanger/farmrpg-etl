import re
import time
from datetime import datetime, timedelta
from typing import Iterable, cast
from zoneinfo import ZoneInfo

import attrs
import structlog
from bs4 import BeautifulSoup, Tag

from ..events import EVENTS
from ..http import client
from ..models.chat import Message

UTC = ZoneInfo("UTC")
SERVER_TIME = ZoneInfo("America/Chicago")

MESSAGE_ID_RE = re.compile(r"^javascript:(?:un)?delChat\((\d+)\)$")
FLAGS_RE = re.compile(r"^(\d+) flags?$")
FORCEPATH_RE = re.compile(r"<strong>\w+path</strong>")
AT_LINK_RE = re.compile(
    r'<a class="close-panel" href="profile.php\?user_name=[^">]+" style="color:teal">(@[^">]+)</a>'
)


log = structlog.stdlib.get_logger(mod="scrapers.chat")


class ParseError(Exception):
    pass


def _parse_chat(room: str, content: bytes) -> Iterable[Message]:
    """Parse the chat HTML into models."""
    # This has a bunch of ugly casts because the type stubs for BS aren't great.
    # (or rather the interface isn't built for strong typing, sigh)
    root = BeautifulSoup(content, "lxml")
    now = datetime.now(tz=SERVER_TIME)
    for elm in root.select("div.chat-txt"):
        # Parse out the timestamp, which is weirdly difficult.
        ts_elm = elm.select_one("span")
        if ts_elm is None:
            raise ParseError(f"Unable to find timestamp: {content.decode()}")
        ts = datetime.strptime(ts_elm.text.strip(), "%I:%M:%S %p").replace(
            year=now.year, month=now.month, day=now.day, tzinfo=now.tzinfo
        )
        if ts > now:
            # Day rollover, this was actually yesterday.
            ts = ts - timedelta(days=1)
        # Find the chat message ID.
        chip_elm = elm.select_one("div.chip")
        if chip_elm is None:
            raise ParseError(f"Unable to find chip: {content.decode()}")
        message_id_a_elm = cast(Tag | None, chip_elm.find_next_sibling("a"))
        if message_id_a_elm is None:
            raise ParseError(f"Unable to find message ID link: {content.decode()}")
        message_id_match = MESSAGE_ID_RE.match(cast(str, message_id_a_elm["href"]))
        if message_id_match is None:
            raise ParseError(f"Unable to parse message ID: {message_id_a_elm['href']}")
        # Then the rest of the stuff is easy.
        emblem_elm = elm.select_one("div.chip-media img")
        if emblem_elm is None:
            raise ParseError(f"Unable to find emblem: {content.decode()}")
        icons_elm = elm.select_one("i.f7-icons")
        if icons_elm is None:
            raise ParseError(f"Unable to find icons: {content.decode()}")
        content_elm = cast(Tag | None, icons_elm.find_next("span"))
        if content_elm is None:
            raise ParseError(f"Unable to find content span: {content.decode()}")
        msg_content = content_elm.decode_contents(formatter="html5")
        msg_content = FORCEPATH_RE.sub("<strong>Forcepath</strong>", msg_content)
        msg_content = AT_LINK_RE.sub(r"\1:", msg_content)
        yield Message(
            room=room,
            id=message_id_match[1],
            ts=ts.astimezone(UTC),
            emblem=cast(str, emblem_elm["src"]).rsplit("/", 1)[-1],
            username=cast(str, emblem_elm["data-username"]),
            content=msg_content,
            deleted="redstripes" in elm["class"],
        )


def _parse_flags(room: str, content: bytes) -> Iterable[Message]:
    """Parse the chat HTML into models."""
    # This has a bunch of ugly casts because the type stubs for BS aren't great.
    # (or rather the interface isn't built for strong typing, sigh)
    root = BeautifulSoup(content, "lxml")
    now = datetime.now(tz=SERVER_TIME)
    for elm in root.select("li"):
        title_elm = elm.select_one(".item-title")
        if title_elm is None:
            raise ParseError(f"Unable to find item title: {content.decode()}")
        after_elm = elm.select_one(".item-after")
        if after_elm is None:
            raise ParseError(f"Unable to find item after: {content.decode()}")
        parts = list(title_elm.stripped_strings)
        ts = datetime.strptime(parts[0], "%b %d, %I:%M:%S %p").replace(
            year=now.year, tzinfo=SERVER_TIME
        )
        if ts > now:
            # Year rollover, this was actually last year.
            ts.replace(year=ts.year - 1)
        flags_match = FLAGS_RE.match(after_elm.string or "")
        yield Message(
            room=room,
            id=str(hash(tuple(parts))),
            ts=ts.astimezone(UTC),
            emblem="",
            username=parts[1],
            content=parts[2][2:],
            flags=int(flags_match[1]) if flags_match else 0,
        )


@attrs.define
class ChatScraper:
    room: str
    flags: bool = False
    last_messages: dict[str, Message] = {}

    async def run(self) -> None:
        log.debug("Starting scrape", room=self.room, flags=self.flags)
        if self.flags:
            resp = await client.get(
                "log.php",
                params={
                    "type": "chat",
                    "room": self.room,
                    "flag": "1",
                },
            )
        else:
            resp = await client.get(
                "worker.php",
                params={
                    "go": "getchat",
                    "room": self.room,
                    "cachebuster": time.time(),
                },
            )
        if resp.status_code != 200:
            log.error(
                "Got an error",
                room=self.room,
                status_code=resp.status_code,
                content=resp.content,
            )
            return
        if resp.content == b"no access":
            log.error("Got a 'no access'", room=self.room, content=resp.content)
            return
        # Parse the HTML.
        parser = _parse_flags if self.flags else _parse_chat
        msgs = list(parser(self.room, resp.content))
        for msg in reversed(msgs):
            log.debug("Got message", room=self.room, flags=self.flags, msg=msg.id)
            last_msg = self.last_messages.get(msg.id)
            if last_msg is not None and last_msg.deleted_ts is not None:
                msg.deleted_ts = last_msg.deleted_ts
            if last_msg is None or msg != last_msg:
                if (
                    last_msg is not None
                    and last_msg.deleted is False
                    and msg.deleted is True
                ):
                    msg.deleted_ts = datetime.now(tz=UTC)
                EVENTS.emit(f"{'flags' if self.flags else 'chat'}.{self.room}", msg=msg)
        self.last_messages = {msg.id: msg for msg in msgs}
        log.debug("Finished scrape", room=self.room, flags=self.flags)
