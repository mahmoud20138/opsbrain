"""Periodic monitoring scheduler for recurring health checks and incident polls.

Runs background tasks at configured intervals to pull telemetry from data
connectors and trigger orchestration pipelines when anomalies arise.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class ScheduledTask(BaseModel):
    """Configuration for a recurring monitoring task."""

    task_id: str
    name: str
    interval_seconds: float = 60.0
    enabled: bool = True
    last_run: datetime | None = None
    run_count: int = 0
    error_count: int = 0
    last_error: str | None = None


class PeriodicScheduler:
    """Async background task scheduler for recurring monitoring.

    Usage::

        scheduler = PeriodicScheduler()
        scheduler.add_task(
            task_id="prom_check",
            name="Prometheus Production Metrics",
            interval_seconds=30.0,
            coro_fn=check_prometheus_metrics,
        )
        await scheduler.start()
        ...
        await scheduler.stop()
    """

    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self._coro_fns: dict[str, Callable[[], Coroutine[Any, Any, Any]]] = {}
        self._running = False
        self._bg_tasks: list[asyncio.Task] = []

    def add_task(
        self,
        task_id: str,
        name: str,
        interval_seconds: float,
        coro_fn: Callable[[], Coroutine[Any, Any, Any]],
        enabled: bool = True,
    ) -> None:
        """Register a new periodic task."""
        self._tasks[task_id] = ScheduledTask(
            task_id=task_id,
            name=name,
            interval_seconds=interval_seconds,
            enabled=enabled,
        )
        self._coro_fns[task_id] = coro_fn
        logger.info("scheduler.task_added", task_id=task_id, interval=interval_seconds)

    def remove_task(self, task_id: str) -> None:
        """Remove a task by ID."""
        self._tasks.pop(task_id, None)
        self._coro_fns.pop(task_id, None)

    async def start(self) -> None:
        """Start all registered scheduled tasks in the background."""
        if self._running:
            return
        self._running = True
        logger.info("scheduler.started", task_count=len(self._tasks))

        for task_id in self._tasks:
            bg_task = asyncio.create_task(self._run_loop(task_id))
            self._bg_tasks.append(bg_task)

    async def stop(self) -> None:
        """Stop all background scheduled tasks."""
        self._running = False
        for t in self._bg_tasks:
            t.cancel()
        await asyncio.gather(*self._bg_tasks, return_exceptions=True)
        self._bg_tasks.clear()
        logger.info("scheduler.stopped")

    async def run_once(self, task_id: str) -> Any:
        """Execute a single task once immediately."""
        task = self._tasks.get(task_id)
        fn = self._coro_fns.get(task_id)
        if not task or not fn:
            raise ValueError(f"Task '{task_id}' not found")

        task.run_count += 1
        task.last_run = datetime.now(UTC)
        try:
            result = await fn()
            return result
        except Exception as exc:
            task.error_count += 1
            task.last_error = str(exc)
            logger.error("scheduler.task_failed", task_id=task_id, error=str(exc))
            raise

    async def _run_loop(self, task_id: str) -> None:
        """Individual task execution loop."""
        while self._running:
            task = self._tasks.get(task_id)
            fn = self._coro_fns.get(task_id)
            if not task or not fn or not task.enabled:
                await asyncio.sleep(1.0)
                continue

            try:
                await self.run_once(task_id)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("scheduler.loop_error", task_id=task_id, error=str(exc))

            try:
                await asyncio.sleep(task.interval_seconds)
            except asyncio.CancelledError:
                break

    def list_tasks(self) -> list[ScheduledTask]:
        """List all tasks and their execution stats."""
        return list(self._tasks.values())
