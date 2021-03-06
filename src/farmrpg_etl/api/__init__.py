from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

# from .auth import login


async def hello_world(request: Request) -> Response:
    return JSONResponse(
        {"hello": "world", "path": str(request.url), "p": request.path_params["p"]}
    )


async def not_found(request: Request) -> Response:
    return Response("", status_code=404)


# routes = [Route("/login", login, methods=["POST"]), Route("/{p:path}", hello_world)]
routes = [Route("/", not_found)]
