from ..events import EVENTS
from ..firebase import set_custom_user_claims
from ..models.user import UserSnapshot, get_custom_claims


@EVENTS.on("new_user_snapshot")
async def on_snap(snap: UserSnapshot, last_snap: UserSnapshot | None):
    # If they have a Firebase ID, update any custom claims.
    if snap.user.firebase_uid:
        # Check if things changed.
        claims = get_custom_claims(snap)
        if last_snap is None or claims != get_custom_claims(last_snap):
            await set_custom_user_claims(snap.user.firebase_uid, claims)
