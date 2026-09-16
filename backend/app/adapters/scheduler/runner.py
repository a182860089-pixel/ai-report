from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.application.pipeline import PipelineUseCases
from app.application.schedule import matching_slot, next_run_at, parse_schedule
from app.application.timefmt import shanghai_date
from app.config import Settings
from app.domain.entities import AdminUser, ScheduleStatus, ScheduledTick
from app.domain.interfaces import Clock, IdentityRepository

log = logging.getLogger("ai_report.scheduler")


class PipelineScheduler:
    def __init__(
        self,
        pipeline: PipelineUseCases,
        identity: IdentityRepository,
        settings: Settings,
        clock: Clock,
    ) -> None:
        self.pipeline = pipeline
        self.identity = identity
        self.settings = settings
        self.clock = clock
        self.last_tick: ScheduledTick | None = None
        self._last_slot: tuple | None = None
        self._stop = asyncio.Event()
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[Any] | None = None

    @property
    def times(self) -> tuple[str, ...]:
        return parse_schedule(self.settings.pipeline_schedule)

    def snapshot(self) -> ScheduleStatus:
        enabled = self.settings.pipeline_scheduler_enabled
        now = self.clock.now()
        return ScheduleStatus(
            enabled=enabled,
            times=self.times,
            timezone="Asia/Shanghai",
            auto_cluster=self.settings.pipeline_auto_cluster,
            next_run_at=next_run_at(now, self.times) if enabled else None,
            last_tick=self.last_tick,
        )

    async def start(self) -> None:
        if not self.settings.pipeline_scheduler_enabled:
            log.info("pipeline scheduler disabled")
            return
        self._stop = asyncio.Event()
        self._task = asyncio.create_task(self._loop(), name="pipeline-scheduler")
        log.info(
            "pipeline scheduler enabled times=%s auto_cluster=%s",
            self.times,
            self.settings.pipeline_auto_cluster,
        )

    async def stop(self) -> None:
        self._stop.set()
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _loop(self) -> None:
        while not self._stop.is_set():
            now = self.clock.now()
            slot = matching_slot(now, self.times)
            if slot is not None:
                key = (shanghai_date(now), slot)
                if key != self._last_slot:
                    try:
                        tick = await self.run_scheduled()
                        log.info(
                            "pipeline tick done cluster=%s runs=%s stories=%s",
                            tick.cluster_status,
                            tick.fetch_run_count,
                            tick.story_count,
                        )
                    except Exception:
                        log.exception("pipeline scheduled tick failed")
                    self._last_slot = key
                    continue
            target = next_run_at(now, self.times)
            delay = (target - self.clock.now()).total_seconds()
            timeout = min(delay if delay > 0.05 else 0.05, 30.0)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=timeout)
                return
            except TimeoutError:
                continue

    async def run_scheduled(self) -> ScheduledTick:
        email = self.settings.admin_email.strip().lower()
        admin = await self.identity.get_admin_by_email(email)
        if admin is None or not admin.is_active:
            started = self.clock.now()
            tick = ScheduledTick(
                started_at=started,
                finished_at=started,
                trigger="schedule",
                fetch_run_count=0,
                skipped_count=0,
                cluster_status="error",
                story_count=0,
                article_count=0,
                slugs=(),
                briefing_date=None,
                error_code="FORBIDDEN",
                error_message="Scheduler admin missing or inactive.",
            )
            self.last_tick = tick
            log.error("pipeline scheduler has no active admin %s", email)
            return tick
        return await self.run_tick(admin, trigger="schedule", ip=None, ua="pipeline-scheduler")

    async def run_tick(
        self,
        admin: AdminUser,
        *,
        trigger: str,
        ip: str | None,
        ua: str | None,
    ) -> ScheduledTick:
        async with self._lock:
            tick = await self.pipeline.scheduled_tick(
                admin,
                auto_cluster=self.settings.pipeline_auto_cluster,
                trigger=trigger,
                ip=ip,
                ua=ua,
            )
            self.last_tick = tick
            return tick
