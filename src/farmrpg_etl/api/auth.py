import json
import os
import time

import google.auth
import httpx
import structlog
from google.cloud.iam_credentials import IAMCredentialsAsyncClient
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..db import objects
from ..models.user import UserSnapshot

log = structlog.stdlib.get_logger(mod="api.auth")

client = httpx.AsyncClient()


FIREBASE_AUD = "https://identitytoolkit.googleapis.com/google.identity.identitytoolkit.v1.IdentityToolkit"  # noqa


async def login(request: Request) -> Response:
    data = await request.json()
    resp = await client.post(
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
        params={"key": os.environ["WEB_API_KEY"]},
        json={
            "email": data["email"],
            "password": data["password"],
            "returnSecureToken": True,
        },
    )
    resp_json = resp.json()
    if resp.status_code != 200:
        return JSONResponse(resp_json, status_code=resp.status_code)
    uid = resp_json["localId"]
    creds = google.auth.default()
    email = creds[0].service_account_email
    now = time.time()
    claims = {}
    # Check for a user in the database matching this uid.
    user_snap = (
        await objects(UserSnapshot).order_by("-ts").first(user__firebase_uid=uid)
    )
    if user_snap is not None:
        if user_snap.is_ranger:
            claims["role"] = "ranger"
        elif user_snap.is_farmhand:
            claims["role"] = "farmhand"
    payload = {
        "iss": email,
        "sub": email,
        "aud": FIREBASE_AUD,
        "uid": uid,
        "iat": now,
        "exp": now + (60 * 60),
        "claims": claims,
    }
    jwt_resp = await IAMCredentialsAsyncClient().sign_jwt(  # type: ignore
        name=f"projects/-/serviceAccounts/{email}",
        payload=json.dumps(payload),
    )
    return JSONResponse({"key_id": jwt_resp.key_id, "signed_jwt": jwt_resp.signed_jwt})
