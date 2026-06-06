"""WebSocket endpoint for live agent event streaming."""
from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.core.events import event_bus, Event, EventType

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/events")
async def events_websocket(websocket: WebSocket) -> None:
    """
    Subscribe to all agent events in real time.
    Send a JSON message {"action": "subscribe", "agent_id": "..."} to filter by agent.
    """
    await websocket.accept()
    event_bus.add_ws_client(websocket)
    logger.info(f"[WebSocket] Client connected: {websocket.client}")

    # Send recent history on connect
    history = event_bus.get_history(limit=50)
    for event in history:
        try:
            await websocket.send_json({
                "id": event.id,
                "type": event.type.value,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
                "agent_id": event.agent_id,
                "historical": True,
            })
        except Exception:
            break

    try:
        while True:
            # Keep connection alive and handle client messages
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                action = msg.get("action")
                if action == "ping":
                    await websocket.send_json({"action": "pong"})
                elif action == "history":
                    agent_id = msg.get("agent_id")
                    limit = int(msg.get("limit", 100))
                    if agent_id:
                        history = event_bus.get_history_for_agent(agent_id, limit=limit)
                    else:
                        history = event_bus.get_history(limit=limit)
                    for event in history:
                        await websocket.send_json({
                            "id": event.id,
                            "type": event.type.value,
                            "data": event.data,
                            "timestamp": event.timestamp.isoformat(),
                            "agent_id": event.agent_id,
                            "historical": True,
                        })
            except (json.JSONDecodeError, ValueError):
                pass

    except WebSocketDisconnect:
        logger.info(f"[WebSocket] Client disconnected: {websocket.client}")
    except Exception as exc:
        logger.warning(f"[WebSocket] Connection error: {exc}")
    finally:
        event_bus.remove_ws_client(websocket)


@router.websocket("/ws/agents/{agent_id}/events")
async def agent_events_websocket(agent_id: str, websocket: WebSocket) -> None:
    """Subscribe to events for a specific agent."""
    await websocket.accept()
    logger.info(f"[WebSocket] Agent {agent_id} stream connected")

    # Wrap the websocket to filter by agent_id
    class AgentFilteredWS:
        def __init__(self, ws: WebSocket, agent_id: str) -> None:
            self._ws = ws
            self._agent_id = agent_id

        async def send_json(self, data: Dict[str, Any]) -> None:
            if data.get("agent_id") == self._agent_id or data.get("historical"):
                await self._ws.send_json(data)

    filtered_ws = AgentFilteredWS(websocket, agent_id)
    event_bus.add_ws_client(filtered_ws)

    # Send recent history for this agent
    history = event_bus.get_history_for_agent(agent_id, limit=50)
    for event in history:
        try:
            await websocket.send_json({
                "id": event.id,
                "type": event.type.value,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
                "agent_id": event.agent_id,
                "historical": True,
            })
        except Exception:
            break

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("action") == "ping":
                    await websocket.send_json({"action": "pong", "agent_id": agent_id})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info(f"[WebSocket] Agent {agent_id} stream disconnected")
    except Exception as exc:
        logger.warning(f"[WebSocket] Agent {agent_id} connection error: {exc}")
    finally:
        event_bus.remove_ws_client(filtered_ws)
