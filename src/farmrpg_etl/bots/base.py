import re

import attrs

from ..events import EVENTS
from ..http import bot_client
from ..models.mailbox import Mail
from ..scrapers.user import UserScraper

BR_RE = re.compile(r"<br\s*/?>")


@attrs.define
class BotMessage:
    msg: Mail
    cmd: str
    args: str | None

    async def user_id(self) -> int:
        snap = await UserScraper(username=self.msg.username).scrape()
        return snap.user.id

    async def reply(self, content: str, subject: str | None = None):
        return await bot_client.post(
            "worker.php",
            params={"go": "sendmessage"},
            data={
                "in_reply_to": self.msg.id,
                "to": self.msg.username,
                "subject": subject or f"RE: {self.msg.subject}",
                "body": content,
            },
        )


def try_dispatch(msg: Mail, line: str) -> tuple[bool, BotMessage]:
    parts = line.split(None, 1)
    if len(parts) > 1:
        cmd, args = parts
    else:
        cmd = parts[0] if parts else ""
        args = None
    # .lower() is for mobile keyboards.
    cmd = cmd.lower()

    # Dispatch if possible.
    bot_msg = BotMessage(msg=msg, cmd=cmd, args=args)
    if not cmd.strip():
        return False, bot_msg
    return EVENTS.emit(f"bot_dm.{cmd}", msg=bot_msg), bot_msg


@EVENTS.on("dm")
async def on_dm(msg: Mail):
    # First parse the first line of the message looking for a command.
    lines = BR_RE.sub("\n", msg.content).splitlines()
    line = lines[0] if lines else ""
    handled, bot_msg = try_dispatch(msg, line)
    if not handled:
        # Try again with the subject line.
        handled, _ = try_dispatch(msg, msg.subject)
    if not handled:
        # Still nope, let them know.
        await bot_msg.reply(
            "Sorry, I didn't understand your request. Please contact Coderanger for assistance."
            f"\n\nDebug info:\n{msg.id=}\n"
        )
