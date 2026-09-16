from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.db.models import (
    AdminUserRow,
    BriefingLedeRow,
    BriefingPulseRow,
    BriefingPulseTopicRow,
    BriefingRow,
    SourceRow,
    StoryCitationRow,
    StoryRow,
    StorySynthesisRow,
    StoryTimelineRow,
    TopicRow,
)
from app.adapters.api.security import Argon2PasswordHasher
from app.application.timefmt import combine_hhmm
from app.config import Settings

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
SEED_DAY = date(2026, 9, 14)


def load_json(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def seed(session: Session, settings: Settings) -> None:
    topics = load_json("topics.json")
    sources = load_json("sources.json")
    briefings = load_json("briefings.json")
    stories = load_json("stories.json")

    topic_ids: dict[str, int] = {}
    for index, row in enumerate(topics):
        existing = session.scalar(select(TopicRow).where(TopicRow.slug == row["slug"]))
        if existing is None:
            existing = TopicRow(
                slug=row["slug"],
                name_zh=row["name"]["zh"],
                name_en=row["name"]["en"],
                blurb_zh=row["blurb"]["zh"],
                blurb_en=row["blurb"]["en"],
                sort_order=index,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(existing)
            session.flush()
        else:
            existing.name_zh = row["name"]["zh"]
            existing.name_en = row["name"]["en"]
            existing.blurb_zh = row["blurb"]["zh"]
            existing.blurb_en = row["blurb"]["en"]
            existing.sort_order = index
            existing.is_active = True
            existing.updated_at = datetime.now(timezone.utc)
        topic_ids[row["slug"]] = existing.id

    source_ids: dict[str, int] = {}
    source_name_ids: dict[str, int] = {}
    for row in sources:
        last_fetch = None
        quarantined = False
        failures = 0
        if row.get("lastFetch") and row["lastFetch"] != "—":
            last_fetch = combine_hhmm(SEED_DAY, row["lastFetch"])
        if row["id"] == "lab-rss":
            last_fetch = None
            quarantined = True
            failures = 2
        existing = session.scalar(select(SourceRow).where(SourceRow.code == row["id"]))
        if existing is None:
            existing = SourceRow(
                code=row["id"],
                name=row["name"],
                status=row["status"],
                last_fetch_at=last_fetch,
                today_count=int(row["todayCount"]),
                consecutive_failures=failures,
                is_quarantined=quarantined,
                detail_zh=row["detail"]["zh"],
                detail_en=row["detail"]["en"],
                homepage_url=row.get("homepageUrl"),
                feed_url=row.get("feedUrl"),
            )
            session.add(existing)
            session.flush()
        else:
            existing.name = row["name"]
            existing.status = row["status"]
            existing.last_fetch_at = last_fetch
            existing.today_count = int(row["todayCount"])
            existing.consecutive_failures = failures
            existing.is_quarantined = quarantined
            existing.detail_zh = row["detail"]["zh"]
            existing.detail_en = row["detail"]["en"]
            existing.homepage_url = row.get("homepageUrl")
            existing.feed_url = row.get("feedUrl")
        source_ids[row["id"]] = existing.id
        source_name_ids[row["name"]] = existing.id

    briefing_ids: dict[str, int] = {}
    for row in briefings:
        day = date.fromisoformat(row["date"])
        published_at = combine_hhmm(day, row["updatedAt"])
        existing = session.scalar(select(BriefingRow).where(BriefingRow.date == day))
        if existing is None:
            existing = BriefingRow(
                date=day,
                weekday_zh=row["weekday"]["zh"],
                weekday_en=row["weekday"]["en"],
                title_zh=row["title"]["zh"],
                title_en=row["title"]["en"],
                more_heading_zh=row["moreHeading"]["zh"],
                more_heading_en=row["moreHeading"]["en"],
                status="published",
                published_at=published_at,
            )
            session.add(existing)
            session.flush()
        else:
            existing.weekday_zh = row["weekday"]["zh"]
            existing.weekday_en = row["weekday"]["en"]
            existing.title_zh = row["title"]["zh"]
            existing.title_en = row["title"]["en"]
            existing.more_heading_zh = row["moreHeading"]["zh"]
            existing.more_heading_en = row["moreHeading"]["en"]
            existing.status = "published"
            existing.published_at = published_at
        briefing_ids[row["date"]] = existing.id
        session.execute(delete(BriefingLedeRow).where(BriefingLedeRow.briefing_id == existing.id))
        session.execute(delete(BriefingPulseTopicRow).where(BriefingPulseTopicRow.briefing_id == existing.id))
        pulse_row = session.get(BriefingPulseRow, existing.id)
        pulse = row["pulse"]
        if pulse_row is None:
            session.add(
                BriefingPulseRow(
                    briefing_id=existing.id,
                    clusters=int(pulse["clusters"]),
                    articles=int(pulse["articles"]),
                    zh_en=pulse["zhEn"],
                    healthy=int(pulse["healthy"]),
                    total_sources=int(pulse["totalSources"]),
                )
            )
        else:
            pulse_row.clusters = int(pulse["clusters"])
            pulse_row.articles = int(pulse["articles"])
            pulse_row.zh_en = pulse["zhEn"]
            pulse_row.healthy = int(pulse["healthy"])
            pulse_row.total_sources = int(pulse["totalSources"])
        for idx, lede in enumerate(row["lede"]):
            session.add(
                BriefingLedeRow(
                    briefing_id=existing.id,
                    sort_order=idx,
                    text_zh=lede["zh"],
                    text_en=lede["en"],
                )
            )
        for idx, topic in enumerate(pulse["topics"]):
            session.add(
                BriefingPulseTopicRow(
                    briefing_id=existing.id,
                    sort_order=idx,
                    name_zh=topic["name"]["zh"],
                    name_en=topic["name"]["en"],
                    count=int(topic["count"]),
                )
            )

    for row in stories:
        section = row["section"]
        rank = row.get("rank")
        if section == "more" or rank == 0:
            rank = None
        existing = session.scalar(select(StoryRow).where(StoryRow.slug == row["slug"]))
        if existing is None:
            existing = StoryRow(
                slug=row["slug"],
                briefing_id=briefing_ids[row["date"]],
                topic_id=topic_ids[row["topicSlug"]],
                section=section,
                rank=rank,
                title_zh=row["title"]["zh"],
                title_en=row["title"]["en"],
                dek_zh=row["dek"]["zh"],
                dek_en=row["dek"]["en"],
            )
            session.add(existing)
            session.flush()
        else:
            existing.briefing_id = briefing_ids[row["date"]]
            existing.topic_id = topic_ids[row["topicSlug"]]
            existing.section = section
            existing.rank = rank
            existing.title_zh = row["title"]["zh"]
            existing.title_en = row["title"]["en"]
            existing.dek_zh = row["dek"]["zh"]
            existing.dek_en = row["dek"]["en"]
        session.execute(delete(StorySynthesisRow).where(StorySynthesisRow.story_id == existing.id))
        session.execute(delete(StoryTimelineRow).where(StoryTimelineRow.story_id == existing.id))
        session.execute(delete(StoryCitationRow).where(StoryCitationRow.story_id == existing.id))
        day = date.fromisoformat(row["date"])
        for idx, item in enumerate(row["synthesis"]):
            session.add(
                StorySynthesisRow(
                    story_id=existing.id,
                    sort_order=idx,
                    text_zh=item["zh"],
                    text_en=item["en"],
                )
            )
        for idx, item in enumerate(row["timeline"]):
            session.add(
                StoryTimelineRow(
                    story_id=existing.id,
                    sort_order=idx,
                    occurred_at=combine_hhmm(day, item["time"]),
                    text_zh=item["text"]["zh"],
                    text_en=item["text"]["en"],
                )
            )
        for idx, item in enumerate(row["sources"]):
            session.add(
                StoryCitationRow(
                    story_id=existing.id,
                    source_id=source_name_ids.get(item["name"]),
                    source_name=item["name"],
                    lang=item["lang"],
                    kind_zh=item["kind"]["zh"],
                    kind_en=item["kind"]["en"],
                    cited_at=combine_hhmm(day, item["time"]),
                    sort_order=idx,
                )
            )

    if settings.admin_password:
        hasher = Argon2PasswordHasher()
        email = settings.admin_email.strip().lower()
        existing = session.scalar(select(AdminUserRow).where(AdminUserRow.email == email))
        password_hash = hasher.hash(settings.admin_password)
        if existing is None:
            session.add(AdminUserRow(email=email, password_hash=password_hash, is_active=True))
        else:
            existing.password_hash = password_hash
            existing.is_active = True

    session.commit()


def main() -> None:
    settings = Settings()
    engine = create_engine(settings.sync_database_url())
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        seed(session, settings)
    print("seed complete")


if __name__ == "__main__":
    main()