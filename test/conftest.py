import asyncio
import os
import urllib.parse
from pathlib import Path
from typing import Callable

import alembic.command
import databases
import pytest
from alembic.config import Config


def pytest_configure(config):
    os.environ["TESTING"] = "true"

    async def recreate_db():
        from farmrpg_etl.db.core.conn import DATABASE_URL

        parsed_url = urllib.parse.urlparse(DATABASE_URL)
        database_name = parsed_url.path.lstrip("/")
        postgres_url = urllib.parse.urlunparse(parsed_url._replace(path="/postgres"))

        database_pg = databases.Database(postgres_url)
        await database_pg.connect()
        await database_pg.execute(f"DROP DATABASE IF EXISTS {database_name}")
        await database_pg.execute(f"CREATE DATABASE {database_name}")
        await database_pg.disconnect()

    asyncio.run(recreate_db())
    config = Config("alembic.ini")
    alembic.command.upgrade(config, "head")


def pytest_unconfigure(config):
    from farmrpg_etl.db.core.conn import database

    asyncio.run(database.disconnect())


@pytest.fixture
def load_fixture(request: pytest.FixtureRequest) -> Callable[[str], bytes]:
    test_path = request.fspath  # type: ignore

    def _load_fixture(filename: str) -> bytes:
        return (
            (Path(test_path) / ".." / "fixtures" / f"{filename}.html")
            .resolve()
            .open("rb")
            .read()
        )

    return _load_fixture
