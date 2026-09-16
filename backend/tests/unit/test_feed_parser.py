from __future__ import annotations

import pytest

from app.adapters.http.parser import XmlFeedParser
from app.domain.exceptions import FeedParseError

PARSER = XmlFeedParser()

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>OpenAI</title>
    <language>en</language>
    <item>
      <title>GPT-5</title>
      <link>https://openai.com/news/gpt-5</link>
      <guid>https://openai.com/news/gpt-5</guid>
      <description>New model</description>
      <pubDate>Tue, 16 Sep 2026 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Agents everywhere</title>
      <link>https://openai.com/news/agents-everywhere</link>
      <guid>https://openai.com/news/agents-everywhere</guid>
      <description>Tool use</description>
    </item>
    <item>
      <title>Skip http</title>
      <link>http://openai.com/insecure</link>
      <guid>http://openai.com/insecure</guid>
    </item>
  </channel>
</rss>
"""

ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="zh">
  <title>HF</title>
  <entry>
    <id>https://huggingface.co/blog/one</id>
    <title>Hello Atom</title>
    <link href="https://huggingface.co/blog/one" rel="alternate"/>
    <summary>Sum</summary>
    <published>2026-09-16T00:00:00Z</published>
  </entry>
  <entry>
    <id>no-link</id>
    <title>Missing https</title>
  </entry>
</feed>
"""


def test_parse_rss_skips_non_https_and_keeps_guid():
    items = PARSER.parse(RSS)
    assert [item.title for item in items] == ["GPT-5", "Agents everywhere"]
    assert items[0].guid == "https://openai.com/news/gpt-5"
    assert items[0].canonical_url == "https://openai.com/news/gpt-5"
    assert items[0].lang == "en"
    assert items[0].published_at is not None
    assert items[1].summary == "Tool use"


def test_parse_atom_and_skip_entry_without_https_link():
    items = PARSER.parse(ATOM)
    assert len(items) == 1
    assert items[0].title == "Hello Atom"
    assert items[0].canonical_url == "https://huggingface.co/blog/one"
    assert items[0].lang == "zh"


def test_empty_body_is_empty_list():
    assert PARSER.parse(b"") == []
    assert PARSER.parse(b"   ") == []


def test_malformed_xml_raises():
    with pytest.raises(FeedParseError) as exc:
        PARSER.parse(b"<rss><channel><item></rss>")
    assert "Malformed XML" in str(exc.value)


def test_unsupported_root_raises():
    with pytest.raises(FeedParseError) as exc:
        PARSER.parse(b"<html><body>nope</body></html>")
    assert "Unsupported feed" in str(exc.value)


def test_guid_falls_back_to_https_link():
    body = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item><title>No guid</title><link>https://example.com/a</link></item>
    </channel></rss>
    """
    items = PARSER.parse(body)
    assert items[0].guid == "https://example.com/a"


def test_xxe_does_not_expand_external_entity():
    body = b"""<?xml version="1.0"?>
    <!DOCTYPE rss [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    <rss version="2.0"><channel><item>
      <title>&xxe;</title>
      <link>https://example.com/x</link>
    </item></channel></rss>
    """
    try:
        items = PARSER.parse(body)
    except FeedParseError:
        return
    dumped = " ".join(item.title + item.summary for item in items)
    assert "root:" not in dumped
    assert "/bin/" not in dumped