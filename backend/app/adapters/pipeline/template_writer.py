from __future__ import annotations

from datetime import date

from app.domain.entities import Article, Citation, Story, Text, TimelineItem, Topic, TopicRef
from app.domain.interfaces import StoryWriter


def _clip(value: str, limit: int) -> str:
    text = (value or "").strip()
    if not text:
        return "—"[:limit] if limit >= 1 else ""
    return text if len(text) <= limit else text[:limit]


class TemplateStoryWriter(StoryWriter):
    def write(self, *, slug: str, day: date, topic: Topic, articles: list[Article]) -> Story:
        citations: list[Citation] = []
        synthesis: list[Text] = []
        timeline: list[TimelineItem] = []
        for article in articles:
            lang = "en" if article.lang == "und" else article.lang
            cited_at = article.published_at or article.fetched_at
            citations.append(
                Citation(
                    name=article.source_name or article.source_code,
                    lang=lang if lang in {"zh", "en"} else "en",
                    kind=Text("采集", "Fetched"),
                    cited_at=cited_at,
                    source_code=article.source_code,
                )
            )
            body = article.summary or article.title
            synthesis.append(Text(_clip(body, 2000), _clip(body, 2000)))
            timeline.append(
                TimelineItem(
                    occurred_at=cited_at,
                    text=Text(_clip(article.title, 400), _clip(article.title, 400)),
                )
            )
        if len(articles) == 1:
            title_s = _clip(articles[0].title, 200)
            dek_s = _clip(articles[0].summary or articles[0].title, 400)
            title = Text(title_s, title_s)
            dek = Text(dek_s, dek_s)
        else:
            n = len(articles)
            title = Text(
                _clip(f"{topic.name.zh} · {n} 条", 200),
                _clip(f"{topic.name.en} · {n} items", 200),
            )
            dek = Text(
                _clip("；".join(item.title for item in articles), 400),
                _clip("; ".join(item.title for item in articles), 400),
            )
        return Story(
            slug=slug,
            date=day,
            topic_slug=topic.slug,
            rank=None,
            section="more",
            title=title,
            dek=dek,
            topic=TopicRef(slug=topic.slug, name=topic.name),
            synthesis=tuple(synthesis),
            timeline=tuple(timeline),
            sources=tuple(citations),
        )
