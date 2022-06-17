import asyncio
from collections import defaultdict
from typing import Callable, Coroutine, TypeVar, overload

import structlog

A = TypeVar("A", bound=Callable[..., Coroutine])


log = structlog.stdlib.get_logger(mod="events")


class EventHub:
    def __init__(self) -> None:
        self.listeners: dict[str, list[Callable[..., Coroutine]]] = defaultdict(list)

    def emit(self, key: str, *args, **kwargs) -> bool:
        found_handler = False
        key_parts = key.split(".")
        for i in range(len(key_parts), 0, -1):
            partial_key = ".".join(key_parts[:i])
            for listener in self.listeners[partial_key]:
                asyncio.create_task(listener(*args, **kwargs))
                found_handler = True
        return found_handler

    @overload
    def on(self, key_pattern: str) -> Callable[[A], A]:
        ...

    @overload
    def on(self, key_pattern: str, fn: Callable[..., Coroutine]) -> None:
        ...

    def on(
        self, key_pattern: str, fn: Callable[..., Coroutine] | None = None
    ) -> Callable[[A], A] | None:
        if fn is None:

            def decorator(fn: A) -> A:
                self.on(key_pattern, fn)
                return fn

            return decorator
        else:
            # log.debug("Adding listener", key=key_pattern, fn=fn)
            self.listeners[key_pattern].append(fn)


EVENTS = EventHub()
