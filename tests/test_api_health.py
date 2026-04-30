import asyncio
import time


def test_health_check_does_not_block_event_loop(monkeypatch):
    import requests
    from src.api.routes import health_check

    class Response:
        status_code = 200

    def slow_get(*_args, **_kwargs):
        time.sleep(0.2)
        return Response()

    monkeypatch.setattr(requests, "get", slow_get)

    async def marker():
        start = time.perf_counter()
        await asyncio.sleep(0.01)
        return time.perf_counter() - start

    async def run_check():
        marker_task = asyncio.create_task(marker())
        health_task = asyncio.create_task(health_check())
        marker_elapsed = await marker_task
        await health_task
        return marker_elapsed

    assert asyncio.run(run_check()) < 0.1
