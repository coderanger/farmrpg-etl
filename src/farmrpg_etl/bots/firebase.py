from ..db import objects
from ..events import EVENTS
from ..firebase import set_custom_user_claims
from ..models.user import User, UserSnapshot
from .base import BotMessage


@EVENTS.on("bot_dm.register")
async def on_register(msg: BotMessage):
    """A user is registering their Firebase UID."""
    # Check that the argument looks like a UID.
    if not (msg.args and len(msg.args) == 28):
        await msg.reply(f"Sorry, {msg.args!r} doesn't appear to be a Firebase UID.")
        return
    user_id = await msg.user_id()
    try:
        rows_updated = (
            await objects(User).filter(id=user_id).update(firebase_uid=msg.args)
        )
        if rows_updated == 0:
            await objects(User).create(id=user_id, firebase_uid=msg.args)

        snap = await objects(UserSnapshot).order_by("-ts").first(user__id=user_id)
        if snap is not None and (snap.is_farmhand or snap.is_ranger):
            role = "ranger" if snap.is_ranger else "farmhand"
            resp = await set_custom_user_claims(
                msg.args, {"username": snap.username, "role": role}
            )
            resp.raise_for_status()
    except Exception:
        await msg.reply(
            "Something went wrong, please contact Coderanger for assistance."
        )
        raise
    await msg.reply("Thank you, your registration has been updated.")
