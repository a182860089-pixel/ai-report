from __future__ import annotations

from datetime import date, datetime, timezone

from app.adapters.pipeline.template_writer import TemplateStoryWriter
from app.application.pipeline import guess_topic
from app.domain.entities import Article, Text, Topic

DAY = date(2026, 9, 16)
NOW = datetime(2026, 9, 16, 1, 0, tzinfo=timezone.utc)


def _topic(slug: str = "agents", zh: str = "\u667a\u80fd\u4f53", en: str = "Agents") -> Topic:
    return Topic(slug=slug, name=Text(zh, en), blurb=Text("", ""), cluster_count=0)


def _article(**overrides) -> Article:
    payload = {
        "source_code": "openai-blog",
        "guid": "https://openai.com/news/x",
        "canonical_url": "https://openai.com/news/x",
        "title": "Hello",
        "summary": "Sum",
        "lang": "en",
        "published_at": None,
        "fetched_at": NOW,
        "source_name": "OpenAI Blog",
        "id": 1,
    }
    payload.update(overrides)
    return Article(**payload)


def test_guess_topic_order_and_default():
    assert guess_topic("GPT-5") == "models"
    assert guess_topic("Agents everywhere", "Tool use") == "agents"
    assert guess_topic("Hugging Face weights") == "open-source"
    assert guess_topic("NVIDIA CUDA hopper") == "chips"
    assert guess_topic("EU AI Act") == "policy"
    assert guess_topic("no needles here") == "research"


def test_writer_single_keeps_title_and_fetched_kind():
    story = TemplateStoryWriter().write(
        slug="20260916-1-models",
        day=DAY,
        topic=_topic("models", "\u6a21\u578b", "Models"),
        articles=[_article(title="GPT-5", summary="New model")],
    )
    assert story.title.zh == "GPT-5"
    assert story.title.en == "GPT-5"
    assert story.section == "more"
    assert story.rank is None
    assert story.sources[0].kind.zh == "\u91c7\u96c6"
    assert story.sources[0].kind.en == "Fetched"
    assert story.sources[0].source_code == "openai-blog"


def test_writer_multi_and_und_lang():
    articles = [
        _article(id=1, title="A", lang="und"),
        _article(id=2, title="B", lang="zh", guid="https://openai.com/news/b"),
    ]
    story = TemplateStoryWriter().write(
        slug="20260916-1-agents",
        day=DAY,
        topic=_topic(),
        articles=articles,
    )
    assert story.title.zh == "\u667a\u80fd\u4f53 \u00b7 2 \u6761"
    assert story.title.en == "Agents \u00b7 2 items"
    assert "\uff1b" in story.dek.zh
    assert story.sources[0].lang == "en"
    assert story.sources[1].lang == "zh"


def test_writer_empty_title_is_emdash():
    story = TemplateStoryWriter().write(
        slug="20260916-1-research",
        day=DAY,
        topic=_topic("research", "\u7814\u7a76", "Research"),
        articles=[_article(title="  ", summary="")],
    )
    assert story.title.zh == "\u2014"
    assert story.title.en == "\u2014"
    assert story.dek.zh == "\u2014"