from datetime import datetime

import pytest
import pytest_asyncio

from farmrpg_etl.db import objects
from farmrpg_etl.models.user import User, UserSnapshot


@pytest_asyncio.fixture(autouse=True)
async def database():
    from farmrpg_etl.db.core.conn import database

    await database.connect()
    yield database
    await database.disconnect()


@pytest.mark.asyncio
async def test_user_join():
    user = await objects(User).create(id=1, firebase_uid="uid1")
    await objects(UserSnapshot).create(
        user=user, username="test1", ts=datetime.utcnow()
    )
    snap = await objects(UserSnapshot).get(user__firebase_uid="uid1")
    assert snap.username == "test1"


@pytest.mark.asyncio
async def test_user_join_two():
    user = await objects(User).create(id=1, firebase_uid="uid1")
    await objects(UserSnapshot).create(
        user=user, username="test1", ts=datetime.utcnow()
    )
    await objects(UserSnapshot).create(
        user=user, username="test2", ts=datetime.utcnow()
    )
    snap = await objects(UserSnapshot).order_by("-ts").first(user__firebase_uid="uid1")
    assert snap
    assert snap.username == "test2"


@pytest.mark.asyncio
async def test_user_get_or_create():
    user, _ = await objects(User).get_or_create(id=1234, defaults={})
    assert user.id == 1234
    snap = UserSnapshot(user=user, username="test1", ts=datetime.utcnow())
    await objects(UserSnapshot).create(snap)
    snap2 = await objects(UserSnapshot).select_related("user").get()
    assert snap2.user.id == 1234


def test_user_pk():
    user = User(id=100)
    assert user.pk == 100  # type: ignore
