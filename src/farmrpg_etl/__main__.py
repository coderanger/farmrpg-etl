import asyncio
import logging
import sys
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import structlog
import typer
import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from farmrpg_etl.models.user import UserSnapshot

from .api import routes
from .db import database
from .events import EVENTS
from .models.chat import Message
from .scrapers.chat import ChatScraper
from .scrapers.user import OnlineScraper
from .tasks import create_periodic_task

UTC = ZoneInfo("UTC")

START_TIME = datetime.now(tz=UTC)

log = structlog.stdlib.get_logger(mod="main")

# Imports just to register data sinks.
from .db import chat, user  # noqa
from .firestore import chat  # noqa


@EVENTS.on("chat")
async def on_chat(msg: Message):
    if msg.ts < START_TIME and msg.deleted_ts is None:
        return
    if msg.deleted:
        print(f"{msg.room} | DELETED {msg.username}: {msg.content}")
    else:
        print(f"{msg.room} | {msg.username}: {msg.content}")


@EVENTS.on("new_user_snapshot")
async def on_snap(snap: UserSnapshot):
    print(f"Updated snapshot for {snap.username} ({snap.user.id})")


async def start_etl():
    log.info("Starting ETL processing")
    create_periodic_task(OnlineScraper().run, 600, name="online-scraper")
    channels = ["help", "global", "spoilers", "trade", "giveaways", "trivia", "staff"]
    # channels = ["global", "help"]
    for channel in channels:
        create_periodic_task(
            ChatScraper(channel).run, 1, name=f"chat-scraper-{channel}"
        )
    # Wait for all chat loading to settle so the current message mappings are in place.
    await asyncio.sleep(30)
    for channel in channels:
        create_periodic_task(
            ChatScraper(channel, flags=True).run, 30, name=f"flags-scraper-{channel}"
        )
    log.info("ETL processing started")


async def on_startup():
    await database.connect()
    EVENTS.emit("startup")
    asyncio.create_task(start_etl(), name="start_etl")


app = Starlette(
    debug=True,
    routes=routes,
    on_startup=[on_startup],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # For now ...
            allow_methods=["GET", "HEAD", "POST"],
        ),
    ],
)


def main(
    tls: Optional[str] = None, debug: bool = False, listen: str = "127.0.0.1:8008"
):
    structlog.configure(
        processors=[
            # If log level is too low, abort pipeline and throw away log entry.
            structlog.stdlib.filter_by_level,
            # Add the name of the logger to event dict.
            structlog.stdlib.add_logger_name,
            # Add log level to event dict.
            structlog.stdlib.add_log_level,
            # Add a timestamp in ISO 8601 format.
            structlog.processors.TimeStamper(fmt="iso"),
            # If the "stack_info" key in the event dict is true, remove it and
            # render the current stack trace in the "stack" key.
            structlog.processors.StackInfoRenderer(),
            # If the "exc_info" key in the event dict is either true or a
            # sys.exc_info() tuple, remove "exc_info" and render the exception
            # with traceback into the "exception" key.
            structlog.processors.format_exc_info,
            # If some value is in bytes, decode it to a unicode str.
            structlog.processors.UnicodeDecoder(),
            # Render the final event dict as JSON.
            structlog.dev.ConsoleRenderer()
            if sys.stdout.isatty()
            else structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if debug else logging.INFO,
    )

    extra_options = {}
    if tls:
        extra_options.update(
            {
                "ssl_keyfile": f"{tls}/tls.key",
                "ssl_certfile": f"{tls}/tls.crt",
            }
        )

    host, port = listen.split(":")

    uvicorn.run(
        app,  # type: ignore https://github.com/encode/starlette/discussions/1513
        host=host,
        port=int(port),
        **extra_options,
    )


if __name__ == "__main__":
    typer.run(main)
