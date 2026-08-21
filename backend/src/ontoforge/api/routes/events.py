"""Server-sent events, so an open tab notices changes made elsewhere (§8)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ontoforge.api.deps import RuntimeDep

router = APIRouter(tags=["events"])

#: Sent when nothing has happened for a while, so proxies keep the socket open.
HEARTBEAT_SECONDS = 20.0


@router.get("/events")
async def stream_events(runtime: RuntimeDep) -> StreamingResponse:
    """A change feed. Every write publishes one event (§6.4).

    Starlette cancels the generator when the client goes away, which unsubscribes
    the queue through the context manager.
    """

    async def generate() -> AsyncIterator[str]:
        async with runtime.events.subscribe() as queue:
            yield f"event: ready\ndata: {json.dumps({'seq': runtime.changelog.last_seq})}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
