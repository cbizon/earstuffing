"""RSS feed generation for podcast apps."""

from datetime import datetime
from email.utils import format_datetime
from xml.etree import ElementTree as ET

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES)


def _it(tag: str) -> str:
    return f"{{{ITUNES}}}{tag}"


def _sub(parent: ET.Element, tag: str, text: str | None = None, **attrs) -> ET.Element:
    el = ET.SubElement(parent, tag, attrs)
    if text is not None:
        el.text = text
    return el


def _hms(seconds: float) -> str:
    s = round(seconds)
    return f"{s // 3600:d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def episode_description(meta: dict) -> str:
    byline = ", ".join(meta["authors"][:3]) + (" et al." if len(meta["authors"]) > 3 else "")
    source = " ".join(filter(None, [byline, f"({meta['year']})" if meta["year"] else "", meta["venue"]]))
    link = f"https://doi.org/{meta['doi']}" if meta["doi"] else meta["url"]
    return "\n\n".join(filter(None, [meta["summary"], source, link]))


def build_feed(episodes: list[dict], feed_cfg: dict, base_url: str) -> bytes:
    """Build RSS XML. Each episode needs meta fields plus audio_bytes and duration."""
    rss = ET.Element("rss", version="2.0")
    channel = _sub(rss, "channel")
    _sub(channel, "title", feed_cfg["title"])
    _sub(channel, "description", feed_cfg["description"])
    _sub(channel, "link", base_url)
    _sub(channel, "language", feed_cfg["language"])
    _sub(channel, _it("author"), feed_cfg["author"])
    _sub(channel, _it("explicit"), "false")
    # Keep the feed out of public podcast directories.
    _sub(channel, _it("block"), "Yes")

    for ep in episodes:
        item = _sub(channel, "item")
        _sub(item, "title", ep["title"])
        _sub(item, "description", episode_description(ep))
        _sub(item, "guid", ep["slug"], isPermaLink="false")
        _sub(item, "pubDate", format_datetime(datetime.fromisoformat(ep["rendered_at"])))
        _sub(item, "enclosure", url=f"{base_url}/episodes/{ep['slug']}.mp3",
             length=str(ep["audio_bytes"]), type="audio/mpeg")
        _sub(item, _it("duration"), _hms(ep["duration"]))
    ET.indent(rss)
    return ET.tostring(rss, encoding="utf-8", xml_declaration=True)
