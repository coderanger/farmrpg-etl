import pytest

from farmrpg_etl.firestore.chat import MENTION_RE


@pytest.mark.parametrize(
    "content,mentions",
    [
        ("@Hnr: hmmm perhaps", ["Hnr"]),
        ("@caption oblivious: me ROPE", ["caption oblivious"]),
        ("@Rattea um, can you speed type 4 in a row then?", ["Rattea"]),
        ("Can someone @ me please?", []),
        ("A longer and weirder @ embedded with a : later", []),
        ("A longer and weirder @embedded with a : later", ["embedded"]),
        ("Two embedded @one and later @two", ["one", "two"]),
        ("@Rattea: &gt;:( sleep is important. you need some.", ["Rattea"]),
        ("Embedded next to each other @one @two", ["one", "two"]),
        ("Embedded and terminated @one: @two:", ["one", "two"]),
        ("@coderanger: one at the start and @Ffff later", ["coderanger", "Ffff"]),
    ],
)
def test_mentions(content, mentions):
    assert MENTION_RE.findall(content) == mentions
