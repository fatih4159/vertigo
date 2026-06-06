"""Unit tests for EventBus."""
import asyncio
import pytest
import pytest_asyncio
from app.core.events import EventBus, Event, EventType

# Use concrete enum values that exist
_EVT_STATE = EventType.AGENT_STARTED
_EVT_ITER = EventType.ITERATION_STARTED


def _make_event(event_type: EventType = _EVT_STATE, agent_id: str = "agent-1") -> Event:
    return Event(type=event_type, agent_id=agent_id, data={"test": True})


@pytest.mark.asyncio
async def test_publish_and_subscribe():
    bus = EventBus()
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(_EVT_STATE, handler)
    ev = _make_event(_EVT_STATE)
    await bus.publish(ev)

    assert len(received) == 1
    assert received[0] is ev


@pytest.mark.asyncio
async def test_publish_no_subscribers():
    """Publishing without subscribers should not raise."""
    bus = EventBus()
    ev = _make_event(_EVT_STATE)
    await bus.publish(ev)  # should not raise


@pytest.mark.asyncio
async def test_multiple_subscribers():
    bus = EventBus()
    results: list[int] = []

    async def h1(event: Event) -> None:
        results.append(1)

    async def h2(event: Event) -> None:
        results.append(2)

    bus.subscribe(_EVT_STATE, h1)
    bus.subscribe(_EVT_STATE, h2)
    await bus.publish(_make_event())

    assert sorted(results) == [1, 2]


@pytest.mark.asyncio
async def test_subscribe_different_types():
    bus = EventBus()
    state_events: list[Event] = []
    iter_events: list[Event] = []

    async def on_state(e: Event) -> None:
        state_events.append(e)

    async def on_iter(e: Event) -> None:
        iter_events.append(e)

    bus.subscribe(_EVT_STATE, on_state)
    bus.subscribe(_EVT_ITER, on_iter)

    await bus.publish(_make_event(_EVT_STATE))
    await bus.publish(_make_event(_EVT_ITER))

    assert len(state_events) == 1
    assert len(iter_events) == 1


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    calls: list[int] = []

    async def handler(event: Event) -> None:
        calls.append(1)

    bus.subscribe(_EVT_STATE, handler)
    bus.unsubscribe(_EVT_STATE, handler)
    await bus.publish(_make_event(_EVT_STATE))

    assert len(calls) == 0


@pytest.mark.asyncio
async def test_event_history_stored():
    bus = EventBus()
    for i in range(5):
        await bus.publish(_make_event())
    assert len(bus._history) == 5


@pytest.mark.asyncio
async def test_event_history_capped():
    bus = EventBus()
    for i in range(1200):
        await bus.publish(_make_event())
    # History should be capped at 1000
    assert len(bus._history) <= 1000


@pytest.mark.asyncio
async def test_synchronous_handler():
    """EventBus should also work with sync handlers."""
    bus = EventBus()
    results: list[Event] = []

    def sync_handler(event: Event) -> None:
        results.append(event)

    bus.subscribe(_EVT_STATE, sync_handler)
    await bus.publish(_make_event(_EVT_STATE))
    assert len(results) == 1
