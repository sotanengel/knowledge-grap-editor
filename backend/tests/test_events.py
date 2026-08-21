from __future__ import annotations

import asyncio

import pytest

from ontoforge.runtime import EventBus


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_a_published_event_reaches_a_subscriber() -> None:
    bus = EventBus()
    async with bus.subscribe() as queue:
        bus.publish({"type": "change", "seq": 1})
        assert await asyncio.wait_for(queue.get(), 1) == {"type": "change", "seq": 1}


@pytest.mark.anyio
async def test_every_subscriber_sees_every_event() -> None:
    bus = EventBus()
    async with bus.subscribe() as first, bus.subscribe() as second:
        bus.publish({"type": "change"})
        assert first.get_nowait() == second.get_nowait()


@pytest.mark.anyio
async def test_leaving_the_context_unsubscribes() -> None:
    bus = EventBus()
    async with bus.subscribe():
        assert bus.subscriber_count == 1
    assert bus.subscriber_count == 0


@pytest.mark.anyio
async def test_a_subscriber_that_fell_behind_is_not_allowed_to_block_the_writer() -> None:
    bus = EventBus()
    async with bus.subscribe() as queue:
        for seq in range(1000):
            bus.publish({"type": "change", "seq": seq})
        assert queue.full()


def test_publishing_with_no_subscribers_is_harmless() -> None:
    EventBus().publish({"type": "change"})
