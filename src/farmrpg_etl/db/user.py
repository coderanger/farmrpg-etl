import cattrs
import structlog

from ..db import objects
from ..events import EVENTS
from ..models.user import User, UserSnapshot

log = structlog.stdlib.get_logger(mod="db.user")


@EVENTS.on("user_snapshot")
async def on_snap(snap: UserSnapshot):
    # Get the latest snapshot for this user (if any) and try to diff them. Later on this
    # will help cut down on no-op Firestore writes but for now it just avoids clogging
    # the database.
    user_id = snap.user.id
    last_snap = await objects(UserSnapshot).order_by("-ts").first(user__id=user_id)
    if last_snap is not None:
        # Check if we need to proceed.
        last_snap_data = cattrs.unstructure(last_snap)
        snap_data = cattrs.unstructure(snap)
        # Delete some fields which are allowed to vary.
        last_snap_data.pop("user")
        snap_data.pop("user")
        last_snap_data.pop("ts")
        snap_data.pop("ts")
        if last_snap_data == snap_data:
            log.debug(
                "Skipping user snapshot save, no-op",
                user_id=user_id,
                username=snap.username,
            )
            return
    snap.user, _ = await objects(User).get_or_create(id=user_id, defaults={})
    try:
        await objects(UserSnapshot).create(snap)
    except Exception:
        log.exception("Error saving snapshot", username=snap.username, user_id=user_id)
        raise
    EVENTS.emit("new_user_snapshot", snap=snap)
