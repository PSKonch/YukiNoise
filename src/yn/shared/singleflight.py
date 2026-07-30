import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

T = TypeVar("T")


class SingleFlight:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    async def run(
        self,
        key: str,
        operation_factory: Callable[[], Awaitable[T]],
    ) -> T:
        task = self._tasks.get(key)
        if task is None:
            task = asyncio.create_task(self._execute(operation_factory, key))
            self._tasks[key] = task

        return cast(T, await asyncio.shield(task))

    async def _execute(
        self,
        operation_factory: Callable[[], Awaitable[T]],
        key: str,
    ) -> T:
        try:
            return await operation_factory()
        finally:
            self._tasks.pop(key, None)
