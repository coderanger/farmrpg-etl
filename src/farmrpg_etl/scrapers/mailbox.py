import asyncio
import re
import urllib.parse
from datetime import datetime
from typing import Iterable, cast

import attrs
import structlog
from bs4 import BeautifulSoup, Tag

from farmrpg_etl.utils.cache import FixedSizeCache

from ..events import EVENTS
from ..http import bot_client
from ..models.mailbox import Mail
from ..utils.datetime import SERVER_TIME, UTC, server_now
from .errors import ParseError

PROFILE_LINK_RE = re.compile(r"^profile.php\?")
TIMESTAMP_RE = re.compile(r"on (.+? [AP]M)(\s|$)")

log = structlog.stdlib.get_logger(mod="scrapers.mailbox")


def _parse_message(id: int, content: bytes) -> Mail:
    root = BeautifulSoup(content, "lxml")
    title_elm = root.select_one("div.card-header")
    if title_elm is None:
        raise ParseError(f"Unable to find title element: {content.decode()}")
    card_inners = root.select("div.card-content-inner")
    if len(card_inners) != 2:
        raise ParseError(f"Wrong number of card inners: {content.decode()}")
    content_elm, meta_elm = card_inners
    profile_link_elm = cast(Tag | None, meta_elm.find("a", href=PROFILE_LINK_RE))
    if profile_link_elm is None:
        raise ParseError(f"Unable to find profile linke: {content.decode()}")
    profile_link = cast(str, profile_link_elm["href"])
    timestamp_str = profile_link_elm.next_sibling
    if timestamp_str is None:
        raise ParseError(f"Unable to find timestamp: {content.decode()}")
    timestamp_match = TIMESTAMP_RE.search(timestamp_str.text)
    if timestamp_match is None:
        raise ParseError(f"Unable to parse timestamp: {timestamp_str}")

    now = server_now()
    ts = datetime.strptime(timestamp_match[1], "%b %d, %I:%M:%S %p").replace(
        tzinfo=SERVER_TIME,
        year=now.year,
    )
    if ts > now:
        # Looped on a year boundary.
        ts = ts.replace(year=ts.year - 1)

    return Mail(
        id=id,
        username=urllib.parse.parse_qs(profile_link.split("?", 1)[-1])["user_name"][0],
        ts=ts.astimezone(UTC),
        subject=title_elm.text.strip(),
        content=content_elm.decode_contents(formatter="html5"),
    )


@attrs.define
class MessageScraper:
    id: int

    async def run(self) -> None:
        resp = await bot_client.get("message.php", params={"id": str(self.id)})
        resp.raise_for_status()
        msg = _parse_message(self.id, resp.content)
        log.info("Received message", username=msg.username, subject=msg.subject)
        EVENTS.emit("dm", msg=msg)


@attrs.define
class MailboxRow:
    id: int
    unread: bool


def _parse_mailbox(content: bytes) -> Iterable[MailboxRow]:
    root = BeautifulSoup(content, "lxml")
    inbox = root.select_one("#inbox")
    if inbox is None:
        raise ParseError(f"Unable to find inbox: {content.decode()}")
    for row in inbox.select("a.item-link"):
        title_elm = row.select_one(".item-title")
        if title_elm is None:
            raise ParseError(f"Unable to find title element: {content.decode()}")
        title_style = cast(str | None, title_elm.get("style"))
        yield MailboxRow(
            id=int(
                urllib.parse.parse_qs(cast(str, row["href"]).split("?", 1)[-1])["id"][0]
            ),
            unread=title_style is not None and "bold" in title_style,
        )


@attrs.define
class MailboxScraper:
    recent_messages: FixedSizeCache[int, bool] = FixedSizeCache(100)

    async def run(self) -> None:
        resp = await bot_client.get("messages.php")
        resp.raise_for_status()
        for row in _parse_mailbox(resp.content):
            log.debug("Found message", id=row.id, unread=row.unread)
            if row.unread and not self.recent_messages.get(row.id):
                log.info("Scraping message", id=row.id)
                self.recent_messages[row.id] = True
                asyncio.create_task(
                    MessageScraper(id=row.id).run(), name=f"message-scraper-{row.id}"
                )
