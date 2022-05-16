from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from .auth import login


async def hello_world(request: Request) -> Response:
    return JSONResponse(
        {"hello": "world", "path": str(request.url), "p": request.path_params["p"]}
    )


routes = [Route("/login", login), Route("/{p:path}", hello_world)]
