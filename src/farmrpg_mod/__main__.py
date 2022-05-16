import asyncio
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import structlog
import uvicorn
from starlette.applications import Starlette

from .api import routes
from .db import database
from .events import EVENTS
from .models.chat import Message
from .scrapers.chat import ChatScraper
from .tasks import create_periodic_task

UTC = ZoneInfo("UTC")

START_TIME = datetime.now(tz=UTC)

log = structlog.stdlib.get_logger(mod="main")

# Imports just to register data sinks.
# from .firestore import chat  # noqa
from .db import chat  # noqa


@EVENTS.on("chat")
async def on_chat(msg: Message):
    if msg.ts < START_TIME and msg.deleted_ts is None:
        return
    if msg.deleted:
        print(f"{msg.room} | DELETED {msg.username}: {msg.content}")
    else:
        print(f"{msg.room} | {msg.username}: {msg.content}")


async def start_etl():
    log.info("Starting ETL processing")
    channels = ["help", "global", "spoilers", "trade", "giveaways", "trivia", "staff"]
    # channels = ["global", "help"]
    for channel in channels:
        create_periodic_task(
            ChatScraper(channel).run, 2, name=f"chat-scraper-{channel}"
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
    asyncio.create_task(start_etl(), name="start_etl")


app = Starlette(
    debug=True,
    routes=routes,
    # on_startup=[on_startup],
)


if __name__ == "__main__":
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
        level=logging.INFO,
        # level=logging.DEBUG,
    )
    uvicorn.run(
        app,  # type: ignore https://github.com/encode/starlette/discussions/1513
        host="127.0.0.1",
        port=8008,
    )
