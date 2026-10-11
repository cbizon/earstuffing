from xml.etree import ElementTree as ET

from earstuffing.feed import ITUNES, build_feed

FEED_CFG = {"title": "Earstuffing", "description": "d", "author": "A", "language": "en-us"}


def episode(slug, rendered_at, authors=("Ann Lee",)):
    return {
        "slug": slug, "title": f"Paper {slug}", "authors": list(authors), "year": "2021",
        "venue": "Cell Syst.", "doi": "10.1/x", "url": "", "summary": "It finds things.",
        "rendered_at": rendered_at, "audio_bytes": 1234, "duration": 3725.4,
    }


def test_build_feed():
    xml = build_feed(
        [episode("b", "2026-10-11T12:00:00+00:00", authors=["A", "B", "C", "D"]),
         episode("a", "2026-10-10T12:00:00+00:00")],
        FEED_CFG,
        "https://pub.example.r2.dev/secret",
    )
    channel = ET.fromstring(xml).find("channel")
    assert channel.find(f"{{{ITUNES}}}block").text == "Yes"
    items = channel.findall("item")
    assert [i.find("guid").text for i in items] == ["b", "a"]
    enc = items[0].find("enclosure")
    assert enc.get("url") == "https://pub.example.r2.dev/secret/episodes/b.mp3"
    assert enc.get("length") == "1234"
    assert items[0].find(f"{{{ITUNES}}}duration").text == "1:02:05"
    desc = items[0].find("description").text
    assert "A, B, C et al. (2021) Cell Syst." in desc
    assert "https://doi.org/10.1/x" in desc
    assert items[0].find("pubDate").text == "Sun, 11 Oct 2026 12:00:00 +0000"
