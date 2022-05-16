import os
import httpx
from starlette.requests import Request
import firebase_admin.auth
from starlette.responses import JSONResponse, Response

client = httpx.AsyncClient()


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
    resp_json = await resp.json()
    if resp.status_code != 200:
        return JSONResponse(resp_json, status_code=resp.status_code)
    uid = resp_json["uid"]
    firebase_admin.auth.create_custom_token

    return JSONResponse({})
