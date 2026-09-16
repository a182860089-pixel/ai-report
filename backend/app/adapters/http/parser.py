from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

from app.domain.entities import ParsedArticle
from app.domain.exceptions import FeedParseError
from app.domain.interfaces import FeedParser

ATOM_NS = "http://www.w3.org/2005/Atom"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return unescape(el.text).strip()


def _child(parent: ET.Element, *names: str) -> ET.Element | None:
    wanted = {name.lower() for name in names}
    for child in list(parent):
        if _local(child.tag).lower() in wanted:
            return child
    return None


def _children(parent: ET.Element, *names: str) -> list[ET.Element]:
    wanted = {name.lower() for name in names}
    return [child for child in list(parent) if _local(child.tag).lower() in wanted]


def _lang(el: ET.Element, inherited: str = "und") -> str:
    raw = el.attrib.get(XML_LANG) or el.attrib.get("lang")
    if not raw:
        raw = _text(_child(el, "language"))
    if not raw:
        return inherited
    low = raw.strip().lower()
    if low.startswith("zh"):
        return "zh"
    if low.startswith("en"):
        return "en"
    return "und"


def _https_link(value: str | None) -> str | None:
    if not value:
        return None
    url = unescape(value).strip()
    if url.startswith("https://") and " " not in url and len(url) <= 500:
        return url
    return None


def _parse_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    try:
        stamp = parsedate_to_datetime(text)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp
    except Exception:
        pass
    iso = text
    if iso.endswith("Z"):
        iso = iso[:-1] + "+00:00"
    try:
        stamp = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp


def _clip(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit]


class XmlFeedParser(FeedParser):
    def parse(self, body: bytes) -> list[ParsedArticle]:
        if not body or not body.strip():
            return []
        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            raise FeedParseError("Malformed XML.") from exc
        tag = _local(root.tag).lower()
        if tag == "rss":
            channel = _child(root, "channel")
            if channel is None:
                return []
            feed_lang = _lang(channel, _lang(root))
            return self._items((_children(channel, "item")), is_atom=False, inherited_lang=feed_lang)
        if tag == "feed":
            feed_lang = _lang(root)
            return self._items(_children(root, "entry"), is_atom=True, inherited_lang=feed_lang)
        raise FeedParseError("Unsupported feed.")

    def _items(self, nodes: list[ET.Element], *, is_atom: bool, inherited_lang: str) -> list[ParsedArticle]:
        out: list[ParsedArticle] = []
        for node in nodes:
            article = self._item(node, is_atom=is_atom, inherited_lang=inherited_lang)
            if article is not None:
                out.append(article)
        return out

    def _item(self, node: ET.Element, *, is_atom: bool, inherited_lang: str) -> ParsedArticle | None:
        link = self._link(node, is_atom=is_atom)
        if link is None:
            return None
        guid_el = _child(node, "guid", "id")
        guid = _text(guid_el) or link
        title = _text(_child(node, "title")) or guid
        summary = _text(_child(node, "description", "summary", "content"))
        published = _parse_time(_text(_child(node, "pubDate", "published", "updated", "date")))
        lang = _lang(node, inherited_lang)
        return ParsedArticle(
            guid=_clip(guid, 500),
            canonical_url=link,
            title=_clip(title, 500),
            summary=_clip(summary, 8000),
            lang=lang,
            published_at=published,
        )

    def _link(self, node: ET.Element, *, is_atom: bool) -> str | None:
        if is_atom:
            preferred: str | None = None
            fallback: str | None = None
            for link in _children(node, "link"):
                href = _https_link(link.attrib.get("href") or _text(link))
                if href is None:
                    continue
                rel = (link.attrib.get("rel") or "alternate").lower()
                if rel == "alternate":
                    preferred = href
                    break
                if fallback is None:
                    fallback = href
            return preferred or fallback
        link_el = _child(node, "link")
        direct = _https_link(_text(link_el) or (link_el.attrib.get("href") if link_el is not None else None))
        if direct:
            return direct
        guid_el = _child(node, "guid")
        return _https_link(_text(guid_el))
