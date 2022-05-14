import asyncio
from asyncio import Task
from typing import Any, Callable, Coroutine

import attrs
import structlog

log = structlog.stdlib.get_logger(mod="tasks")


@attrs.define
class PeriodicTask:
    _task: Task
    _is_stopping: list[bool]

    def stop(self) -> None:
        self._is_stopping[0] = True

    def __getattribute__(self, name: str) -> Any:
        return getattr(self._task, name)


def create_periodic_task(
    coro: Callable[[], Coroutine], interval: int | float, *, name: str | None = None
):
    is_stopping = [False]

    async def wrapper():
        while not is_stopping[0]:
            try:
                await coro()
            except Exception:
                log.error("Error in periodic task", exc_info=True, task_name=name)
            await asyncio.sleep(interval)

    task = asyncio.create_task(wrapper(), name=name)
    return PeriodicTask(task, is_stopping)
