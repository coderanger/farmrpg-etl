from ..events import EVENTS
from .base import BotMessage


@EVENTS.on("bot_dm.ping")
async def on_ping(msg: BotMessage):
    await msg.reply("pong")


@EVENTS.on("bot_dm.userinfo")
async def on_userinfo(msg: BotMessage):
    await msg.reply(f"Your user ID is {await msg.user_id()}")
