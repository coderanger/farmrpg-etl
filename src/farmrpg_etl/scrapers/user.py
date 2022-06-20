import asyncio
import re
import urllib.parse
from typing import Iterable, Literal, cast

import attrs
import structlog
from bs4 import BeautifulSoup, Tag

from ..events import EVENTS
from ..http import client
from ..models.user import User, UserSnapshot
from ..utils.datetime import now
from .errors import ParseError

FRIENDS_LINK_RE = re.compile(r"^members.php\?type=friended&id=(\d+)$")
ONLINE_PROFILE_RE = re.compile(r"^profile.php\?")

log = structlog.stdlib.get_logger(mod="scrapers.user")


def _parse_role(root: BeautifulSoup) -> Literal["farmhand", "ranger"] | None:
    """Parse profile bagdes to find a role badge."""
    badges_card_elm = root.select_one(".card")
    if badges_card_elm is None:
        return None
    admin_image_elm = badges_card_elm.select_one("img[src='/img/items/admin.png']")
    if admin_image_elm is None:
        return None
    role_stong_elm = cast(Tag | None, admin_image_elm.find_next_sibling("strong"))
    if role_stong_elm is None:
        raise ParseError("No role strong found")
    role = role_stong_elm.text.strip()
    if role == "Farm Hand":
        return "farmhand"
    elif role == "Ranger" or role == "Admin":
        return "ranger"
    raise ParseError(f"Unknown role string: {role!r}")


def _parse_profile(username: str, content: bytes) -> UserSnapshot:
    root = BeautifulSoup(content, "lxml")
    # Parse user ID from the friends link.
    friends_a_elm = cast(Tag | None, root.find("a", href=FRIENDS_LINK_RE))
    if friends_a_elm is None:
        raise ParseError(f"Unable to find friends link: {content.decode()}")
    friends_href = cast(str, friends_a_elm["href"])
    user_id_match = FRIENDS_LINK_RE.match(friends_href)
    if user_id_match is None:
        # This should be impossible, it's the same regex as used to find it.
        raise ParseError("Friends link regex did not match")
    user_id = int(user_id_match.group(1))
    # Grab the role.
    role = _parse_role(root)
    # Build the snapshot.
    return UserSnapshot(
        user=User(id=user_id),
        ts=now(),
        username=username,  # TODO: This should parse from the profile itself for casing differences.
        is_farmhand=role == "farmhand",
        is_ranger=role == "ranger",
    )


def _parse_online(content: bytes) -> Iterable[str]:
    root = BeautifulSoup(content, "lxml")
    for elm in root.find_all("a", href=ONLINE_PROFILE_RE):
        href = cast(str, elm["href"])
        qs = urllib.parse.parse_qs(href.split("?", 1)[1])
        yield qs["user_name"][0]


@attrs.define
class UserScraper:
    username: str

    # This is used when the bot receives a DM to get an up-to-date user ID.
    async def scrape(self) -> UserSnapshot:
        resp = await client.get("profile.php", params={"user_name": self.username})
        resp.raise_for_status()
        return _parse_profile(self.username, resp.content)

    async def run(self) -> None:
        log.debug("Starting user scrape", username=self.username)
        snap = await self.scrape()
        EVENTS.emit("user_snapshot", snap=snap)
        log.debug("Finished user scrape", username=self.username, user_id=snap.user.id)


@attrs.define
class OnlineScraper:
    async def run(self) -> None:
        log.debug("Starting online scrape")
        resp = await client.get("online.php")
        resp.raise_for_status()
        online = _parse_online(resp.content)
        # For each online user, scrape them.
        for username in online:
            asyncio.create_task(
                UserScraper(username=username).run(), name=f"user-scraper-{username}"
            )
            await asyncio.sleep(0.1)

        log.debug("Finished online scrape")


@attrs.define
class StaffListScraper:
    """Make sure staff are always tracked."""

    async def run(self) -> None:
        log.debug("Starting staff scrape")
        resp = await client.get("members.php", params={"type": "staff"})
        resp.raise_for_status()
        staff = _parse_online(resp.content)
        # For each staff user, scrape them.
        for username in staff:
            asyncio.create_task(
                UserScraper(username=username).run(), name=f"user-scraper-{username}"
            )
            await asyncio.sleep(0.1)

        log.debug("Finished staff scrape")
