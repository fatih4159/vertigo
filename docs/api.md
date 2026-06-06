# API Reference

Base URL: `http://localhost:8000/api/v1`

All endpoints accept and return JSON unless noted.

## Agents

### Create Agent

`POST /agents`

```json
{
  "name": "My Agent",
  "masterprompt": "You are an expert...",
  "model_name": "qwen2.5-coder:latest",
  "project_id": null,
  "config": {}
}
```

Response `201`:
```json
{
  "id": "uuid",
  "name": "My Agent",
  "masterprompt": "...",
  "state": "IDLE",
  "model_name": "qwen2.5-coder:latest",
  "config_json": {},
  "project_id": null,
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

### Start Agent

`POST /agents/{id}/start`

```json
{
  "mode": "run_forever",
  "n_iterations": null,
  "goal": "Refactor the authentication module"
}
```

`mode` values: `run_forever`, `run_until_goal`, `run_n_iterations`, `manual_step`

### Chat with Agent

`POST /agents/{id}/chat`

```json
{ "message": "What did you accomplish in the last iteration?" }
```

Response:
```json
{
  "agent_id": "uuid",
  "message": "What did...",
  "response": "In the last iteration I..."
}
```

## Memory

### List Memory Entries

`GET /agents/{id}/memory?memory_type=short&limit=100`

`memory_type`: `short`, `mid`, `long` (optional)

### Memory Stats

`GET /agents/{id}/memory/stats`

```json
{
  "agent_id": "uuid",
  "counts_by_type": {"short": 12, "mid": 5, "long": 2}
}
```

## Tools

### Execute Tool

`POST /tools/execute`

```json
{
  "tool_name": "run_command",
  "args": {"command": "pytest tests/ -x"}
}
```

Response:
```json
{
  "tool": "run_command",
  "success": true,
  "output": "5 passed in 1.2s",
  "error": null,
  "duration_ms": 1234.5,
  "metadata": {}
}
```

## Models

### Pull Model

`POST /models/pull`

Returns NDJSON stream:
```
{"status": "pulling manifest"}
{"status": "downloading", "completed": 1024, "total": 4096000000}
...
{"status": "success"}
```

## WebSocket

Connect to `ws://localhost:8000/ws`

All events follow this schema:
```json
{
  "id": "uuid",
  "type": "iteration_start",
  "data": { "number": 5, "goal": "..." },
  "timestamp": "2025-01-01T12:00:00",
  "agent_id": "agent-uuid"
}
```

Event types:
- `state_change` — agent state transition
- `iteration_start` — new iteration began
- `iteration_end` — iteration completed
- `tool_call` — tool invocation
- `tool_result` — tool result received
- `error` — error occurred
- `memory_update` — memory was written
- `chat` — user message or agent response
