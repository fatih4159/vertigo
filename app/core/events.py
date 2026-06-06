from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Callable, Optional
from datetime import datetime
import asyncio
import uuid


class EventType(str, Enum):
    AGENT_STARTED = "agent.started"
    AGENT_PAUSED = "agent.paused"
    AGENT_RESUMED = "agent.resumed"
    AGENT_STOPPED = "agent.stopped"
    ITERATION_STARTED = "iteration.started"
    ITERATION_FINISHED = "iteration.finished"
    TOOL_STARTED = "tool.started"
    TOOL_FINISHED = "tool.finished"
    MEMORY_UPDATED = "memory.updated"
    USER_INTERVENTION = "user.intervention"
    ERROR_OCCURRED = "error.occurred"
    PLAN_CREATED = "plan.created"
    GOAL_ACHIEVED = "goal.achieved"
    CAPABILITY_GAP_DETECTED = "capability.gap"
    NEW_TOOL_GENERATED = "tool.generated"
    NEW_SKILL_GENERATED = "skill.generated"


@dataclass
class Event:
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: Optional[str] = None


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: List[Event] = []
        self._ws_clients: List[Any] = []

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        key = event_type.value
        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        key = event_type.value
        if key in self._subscribers:
            try:
                self._subscribers[key].remove(handler)
            except ValueError:
                pass

    async def publish(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

        handlers = self._subscribers.get(event.type.value, [])
        tasks = []
        for h in handlers:
            if asyncio.iscoroutinefunction(h):
                tasks.append(asyncio.create_task(h(event)))
            else:
                tasks.append(asyncio.create_task(asyncio.to_thread(h, event)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Broadcast to WebSocket clients
        payload = {
            "id": event.id,
            "type": event.type.value,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "agent_id": event.agent_id,
        }
        dead_clients = []
        for ws in list(self._ws_clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead_clients.append(ws)
        for ws in dead_clients:
            self.remove_ws_client(ws)

    def add_ws_client(self, ws: Any) -> None:
        self._ws_clients.append(ws)

    def remove_ws_client(self, ws: Any) -> None:
        if ws in self._ws_clients:
            self._ws_clients.remove(ws)

    def get_history(self, limit: int = 100) -> List[Event]:
        return self._history[-limit:]

    def get_history_for_agent(self, agent_id: str, limit: int = 100) -> List[Event]:
        filtered = [e for e in self._history if e.agent_id == agent_id]
        return filtered[-limit:]


event_bus = EventBus()
