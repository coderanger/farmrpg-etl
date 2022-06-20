from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from farmrpg_etl.scrapers.user import _parse_online, _parse_profile


@pytest.fixture
def profile_ryber(load_fixture) -> bytes:
    return load_fixture("profile_ryber")


@pytest.fixture
def online(load_fixture) -> bytes:
    return load_fixture("online")


@pytest.fixture
def members_staff(load_fixture) -> bytes:
    return load_fixture("members_staff")


@freeze_time("2022-04-17 23:59:59")
def test_parse_profile_ryber(profile_ryber):
    snap = _parse_profile("RybeR", profile_ryber)
    assert snap.user.id == 4153
    assert snap.ts == datetime(2022, 4, 17, 23, 59, 59, tzinfo=ZoneInfo(key="UTC"))
    assert snap.username == "RybeR"
    assert snap.is_farmhand is False
    assert snap.is_ranger is True


def test_parse_online(online):
    online = list(_parse_online(online))
    assert len(online) == 1626
    assert online[0] == "-sam-"
    assert online[-1] == "Zzck"


def test_parse_staff(members_staff):
    staff = list(_parse_online(members_staff))
    assert len(staff) == 25
    assert staff[0] == "Atomiccow"
    assert staff[-1] == "wsey54"
