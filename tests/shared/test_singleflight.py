import asyncio

import pytest

from yn.shared.singleflight import SingleFlight


def test_coalesces_concurrent_operations() -> None:
    async def run() -> None:
        singleflight = SingleFlight()
        operation_started = asyncio.Event()
        release_operation = asyncio.Event()
        calls = 0

        async def operation() -> str:
            nonlocal calls
            calls += 1
            operation_started.set()
            await release_operation.wait()
            return "result"

        first = asyncio.create_task(singleflight.run("key", operation))
        await operation_started.wait()
        second = asyncio.create_task(singleflight.run("key", operation))
        await asyncio.sleep(0)
        release_operation.set()

        results = await asyncio.gather(first, second)
        assert list(results) == ["result", "result"]
        assert calls == 1

    asyncio.run(run())


def test_removes_failed_operation() -> None:
    async def run() -> None:
        singleflight = SingleFlight()
        calls = 0

        async def operation() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("failed")
            return "result"

        with pytest.raises(RuntimeError, match="failed"):
            await singleflight.run("key", operation)

        assert await singleflight.run("key", operation) == "result"
        assert calls == 2

    asyncio.run(run())
