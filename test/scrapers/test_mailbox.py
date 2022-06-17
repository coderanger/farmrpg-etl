from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from farmrpg_etl.scrapers.mailbox import _parse_mailbox, _parse_message


@pytest.fixture
def mailbox(load_fixture) -> bytes:
    return load_fixture("mailbox")


@pytest.fixture
def message(load_fixture) -> bytes:
    return load_fixture("message")


@pytest.fixture
def message_year(load_fixture) -> bytes:
    return load_fixture("message_year")


@freeze_time("2022-06-16 23:59:59")
def test_parse_message(message):
    msg = _parse_message(100, message)
    assert msg.id == 100
    assert msg.username == "Lazyforlife"
    assert msg.ts == datetime(2022, 5, 25, 18, 29, 59, tzinfo=ZoneInfo("UTC"))
    assert msg.subject == "trade ratio bot"
    assert (
        msg.content
        == """hey there, ffff pointed me to you for 3rd party sites. I think you run buddy.farm right? super cool site!<br>
<br>
I'm thinking of making something to track trade ratios, ffff recommended that I talk to you about how you scrap data out of the game<br>
<br>
you open to chatting? Is it an extension? headless browser? What's been allowed/disallowed? <br>
<br>
thanks in advance"""  # noqa
    )


@freeze_time("2023-01-02 00:00:00")
def test_parse_message_year(message_year):
    msg = _parse_message(100, message_year)
    assert msg.ts == datetime(2022, 12, 31, 18, 59, 59, tzinfo=ZoneInfo("UTC"))


def test_parse_mailbox(mailbox):
    rows = list(_parse_mailbox(mailbox))
    assert len(rows) == 5

    assert rows[0].id == 782186
    assert rows[0].unread is True

    assert rows[1].id == 781884
    assert rows[1].unread is True

    assert rows[2].id == 781847
    assert rows[2].unread is False

    assert rows[3].id == 781837
    assert rows[3].unread is False

    assert rows[4].id == 781831
    assert rows[4].unread is False
