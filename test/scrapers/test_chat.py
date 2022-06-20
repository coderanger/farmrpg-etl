from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from farmrpg_etl.scrapers.chat import _parse_chat, _parse_flags


@pytest.fixture
def help_chat(load_fixture) -> bytes:
    return load_fixture("chat_help")


@pytest.fixture
def complex_chat(load_fixture) -> bytes:
    return load_fixture("chat_complex")


@pytest.fixture
def deleted_chat(load_fixture) -> bytes:
    return load_fixture("chat_deleted")


@pytest.fixture
def long_chat(load_fixture) -> bytes:
    return load_fixture("chat_long")


@pytest.fixture
def flags(load_fixture) -> bytes:
    return load_fixture("flags")


@pytest.fixture
def chat_day_rollover(load_fixture) -> bytes:
    return load_fixture("chat_day_rollover")


@freeze_time("2022-04-17 23:59:59")
def test_parse_chat(help_chat):
    chats = list(_parse_chat("help", help_chat))
    assert len(chats) == 100

    assert chats[0].room == "help"
    assert chats[0].id == "5364278"
    assert chats[0].ts == datetime(2022, 4, 17, 1, 44, 56, tzinfo=ZoneInfo(key="UTC"))
    assert chats[0].username == "Nubishi"
    assert chats[0].emblem == "def.png"
    assert (
        chats[0].content == "How many corn does it take usually to get the Runestone?"
    )
    assert chats[0].deleted is False


@freeze_time("2022-04-17 23:59:59")
def test_parse_complex_chat(complex_chat):
    chats = list(_parse_chat("", complex_chat))
    assert len(chats) == 2

    assert chats[0].id == "5363775"
    assert chats[0].ts == datetime(2022, 4, 17, 1, 28, 15, tzinfo=ZoneInfo(key="UTC"))
    assert chats[0].username == "coderanger"
    assert chats[0].emblem == "Octopus96.png"
    assert chats[0].content == '<i style="color:teal">coderanger also testing this</i>'
    assert chats[0].deleted is False

    assert chats[1].id == "5363757"
    assert chats[1].ts == datetime(2022, 4, 17, 1, 27, 32, tzinfo=ZoneInfo(key="UTC"))
    assert chats[1].username == "coderanger"
    assert chats[1].emblem == "Octopus96.png"
    assert (
        chats[1].content
        == 'Testing some chat things, <a class="close-panel" href="item.php?id=48">'
        '<img class="itemimgsm" src="/img/items/potato.png"></a>, '
        '<a class="external chatlink" href="https://google.com," rel="noopener noreferrer" target="_blank">[LINK]</a> ✨'
    )
    assert chats[1].deleted is False


@freeze_time("2022-04-17 23:59:59")
def test_parse_chat_deleted(deleted_chat):
    chats = list(_parse_chat("", deleted_chat))
    assert len(chats) == 1

    assert chats[0].id == "5365014"
    assert chats[0].ts == datetime(2022, 4, 17, 2, 8, 22, tzinfo=ZoneInfo(key="UTC"))
    assert chats[0].username == "coderanger"
    assert chats[0].emblem == "Octopus96.png"
    assert chats[0].content == "A message so I can delete it."
    assert chats[0].deleted is True


@freeze_time("2022-04-17 23:59:59")
def test_parse_chat_long(long_chat):
    chats = list(_parse_chat("", long_chat))
    assert len(chats) == 3

    assert chats[0].id == "5365274"
    assert chats[0].ts == datetime(2022, 4, 17, 2, 16, 37, tzinfo=ZoneInfo(key="UTC"))
    assert chats[0].username == "coderanger"
    assert chats[0].emblem == "Octopus96.png"
    assert (
        chats[0].content
        == "I also need a long message to test so: Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do "
        "eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
        "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit "
        "in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non "
        "proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
    )
    assert chats[0].deleted is False

    assert chats[2].id == "5365182"
    assert chats[2].ts == datetime(2022, 4, 17, 2, 13, 50, tzinfo=ZoneInfo(key="UTC"))
    assert chats[2].username == "Ffff"
    assert chats[2].emblem == "StrangeEgg96.png"
    assert (
        chats[2].content
        == '@coderanger: Parse this! <a class="no-animation close-panel" '
        'href="wiki.php?page=((inferno sphere" style="color:crimson; font-weight:bold; '
        'text-decoration:underline">((inferno sphere</a><a class="no-animation close-panel" '
        'href="wiki.php?page=))" style="color:crimson; font-weight:bold; '
        'text-decoration:underline">))</a> <a class="no-animation close-panel" '
        'href="wiki.php?page= [Ffff] " style="color:crimson; font-weight:bold; '
        'text-decoration:underline"> [Ffff] </a> ((puff<a class="no-animation close-panel" '
        'href="wiki.php?page=" style="color:crimson; font-weight:bold; text-decoration:'
        'underline"></a>er)) pea&scy;ock -blam!-'
    )
    assert chats[2].deleted is False


@freeze_time("2022-06-20 05:20:00")
def test_parse_chat_day_rollover(chat_day_rollover):
    chats = list(_parse_chat("", chat_day_rollover))
    assert len(chats) == 9

    assert chats[0].ts == datetime(2022, 6, 20, 4, 53, 17, tzinfo=ZoneInfo(key="UTC"))
    assert chats[0].content == "one"

    assert chats[1].ts == datetime(2022, 6, 20, 4, 52, 18, tzinfo=ZoneInfo(key="UTC"))
    assert chats[1].content == "two"

    assert chats[2].ts == datetime(2022, 6, 20, 4, 0, 30, tzinfo=ZoneInfo(key="UTC"))
    assert chats[2].content == "three"

    assert chats[3].ts == datetime(2022, 6, 20, 3, 57, 41, tzinfo=ZoneInfo(key="UTC"))
    assert chats[3].content == "four"

    assert chats[4].ts == datetime(2022, 6, 19, 5, 11, 1, tzinfo=ZoneInfo(key="UTC"))
    assert chats[4].content == "five"

    assert chats[5].ts == datetime(2022, 6, 19, 5, 5, 47, tzinfo=ZoneInfo(key="UTC"))
    assert chats[5].content == "six"

    assert chats[6].ts == datetime(2022, 6, 19, 3, 30, 23, tzinfo=ZoneInfo(key="UTC"))
    assert chats[6].content == "seven"

    assert chats[7].ts == datetime(2022, 6, 18, 16, 29, 50, tzinfo=ZoneInfo(key="UTC"))
    assert chats[7].content == "eight"

    assert chats[8].ts == datetime(2022, 6, 18, 15, 33, 55, tzinfo=ZoneInfo(key="UTC"))
    assert chats[8].content == "nine"


@freeze_time("2022-04-17 23:59:59")
def test_parse_flags(flags):
    chats = list(_parse_flags("", flags))
    assert len(chats) == 59

    assert chats[0].ts == datetime(2022, 4, 17, 1, 25, 32, tzinfo=ZoneInfo(key="UTC"))
    assert chats[0].username == "k-swag"
    assert (
        chats[0].content
        == "Looking for (((Egg 06))? Well look no further. Head over to the Trade chat to purchase this "
        "in-demand egg for the affordable price of 180g."
    )
    assert chats[0].flags == 2

    assert chats[1].ts == datetime(2022, 4, 16, 22, 37, 4, tzinfo=ZoneInfo(key="UTC"))
    assert chats[1].username == "Katiepie"
    assert chats[1].content == "Plz have straw"
    assert chats[1].flags == 1
