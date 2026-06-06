# AAOS Architecture

## Overview

AAOS is designed around three core principles:
1. **Autonomous execution** — agents run iterative loops without human intervention
2. **Self-extension** — agents can detect capability gaps and generate new tools/skills
3. **Observable operation** — every action is logged, stored, and streamed in real-time

## Core Components

### Agent Runner (`app/agent/runner.py`)

The `AgentRunner` is the heart of AAOS. It executes the following loop:

```
IDLE
  │ start()
  ▼
RUNNING
  │
  ├── build_context()     ← short/mid/long memory + recent events
  │
  ├── plan()              ← LLM produces JSON plan (goal + steps)
  │
  ├── execute_steps()     ← iterate over plan steps
  │   ├── call tool
  │   ├── store result
  │   └── publish event
  │
  ├── update_memory()     ← summarize iteration into memory
  │
  └── evaluate_goal()     ← decide whether to continue or stop
```

Run modes:
- `run_forever` — loop until manually stopped
- `run_until_goal` — loop until the LLM declares goal met
- `run_n_iterations` — stop after N iterations
- `manual_step` — execute exactly one iteration then stop

### State Machine (`app/core/state_machine.py`)

Valid state transitions:

```
IDLE → RUNNING
RUNNING → PAUSED, STOPPED, ERROR, WAITING_FOR_APPROVAL
PAUSED → RUNNING, STOPPED
WAITING_FOR_APPROVAL → RUNNING, PAUSED, STOPPED
ERROR → IDLE, STOPPED
STOPPED → IDLE
```

The state machine enforces all transitions and records a full history.

### Event Bus (`app/core/events.py`)

A publish/subscribe system that:
- Broadcasts events to in-process subscribers
- Stores up to 1,000 events in memory
- Forwards all events to connected WebSocket clients

Event types include: `STATE_CHANGE`, `ITERATION_START`, `ITERATION_END`, `TOOL_CALL`, `TOOL_RESULT`, `ERROR`, `MEMORY_UPDATE`, `CHAT`.

### Memory System

Three memory tiers stored in SQLite:

| Tier | Purpose | Max entries | Retention |
|---|---|---|---|
| Short-term | Current context window | 50 | Ephemeral, per-run |
| Mid-term | Session state | 200 | Across iterations |
| Long-term | Accumulated knowledge | Unlimited | Persistent |

Memory entries contain: key, content, type, access_count, created_at, accessed_at, optional embedding.

### Planner (`app/agent/planner.py`)

The planner constructs an LLM prompt that includes:
- Agent masterprompt
- Current memory context
- Available tool schemas
- Recent iteration history
- Current goal

It parses the LLM response into a structured `Plan` with `Step` objects, each specifying which tool to call and with what arguments.

### Tool Registry (`app/tools/base.py`)

All tools register themselves in a global `tool_registry`. Each tool provides:
- `name` and `description`
- `input_schema` (JSON Schema)
- `permissions` list (read, write, execute, network, git)
- `execute()` method returning `ToolResult`

### Self-Extension System (`app/extensions/`)

```
CapabilityDetector
  │ Analyses iteration failures and tool usage patterns
  │ Returns: List[CapabilityGap]
  ▼
ToolGenerator / SkillGenerator
  │ Sends gap description to Ollama
  │ Generates code, generates tests
  ▼
Sandbox
  │ Static pattern check (no os.system, eval, etc.)
  │ AST syntax check + forbidden import scan
  │ Subprocess test run with timeout
  ▼
Repository (DB storage)
  │ Stores validated tool/skill code in generated_tools / generated_skills
  ▼
SelfImprovementAnalyzer
  │ Analyses success rates, token efficiency, tool performance
  │ Stores report in long-term memory
```

## Data Flow

### Agent Start

```
POST /api/v1/agents/{id}/start
  │
  ├── Load agent from DB
  ├── Create AgentRunner
  ├── Launch run() as background task
  └── Return immediately with status=started

Background:
  AgentRunner.run()
    │
    ├── Transition: IDLE → RUNNING
    ├── Publish STATE_CHANGE event
    ├── Loop:
    │   ├── _run_single_iteration()
    │   │   ├── Planner.plan()
    │   │   ├── For each step: tool.run()
    │   │   └── Store Iteration + ToolCall records
    │   └── check stop condition
    └── Transition: RUNNING → STOPPED
```

### WebSocket Event Flow

```
AgentRunner
  └── event_bus.publish(event)
        └── WebSocketManager.broadcast(event)
              └── All connected clients receive JSON event
```

## Database Schema

See `app/database/models.py`. Tables:

- `projects` — optional project grouping
- `agents` — agent config + state
- `iterations` — per-iteration records with plan/result
- `tool_calls` — individual tool invocations within an iteration
- `memory_entries` — short/mid/long memory
- `agent_events` — event log
- `git_actions` — git operations requiring confirmation
- `generated_tools` — LLM-generated tool code
- `generated_skills` — LLM-generated skill code

## Frontend Architecture

The React UI uses:
- **Vite** for dev server with proxy to backend
- **React Router v6** for client-side routing
- **Zustand** for global state (persisted to localStorage)
- **useWebSocket** hook for live event streaming
- **axios** client with error normalization
- **CodeMirror** for masterprompt editing
- **Tailwind CSS** with custom dark theme

Key data flows:
1. App mounts → fetches agent list → populates Zustand store
2. WebSocket connects → events stream → stored in `wsEvents`
3. AgentPage polls every 2s for agent status updates
4. Components read from store, dispatch API calls
