# AAOS — AGI Agent Operating System

A production-grade autonomous agent platform built on FastAPI, SQLAlchemy, Ollama, React/Vite, and a self-extension architecture.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AAOS Architecture                           │
├──────────────────────────┬──────────────────────────────────────────┤
│     React UI (Vite)      │           FastAPI Backend                │
│  ┌────────────────────┐  │  ┌─────────────────────────────────┐    │
│  │ Dashboard          │  │  │ REST API  /api/v1/               │    │
│  │ AgentPage          │◄─┼──┤   agents   memory  tools  models│    │
│  │ MemoryPage         │  │  │   git                           │    │
│  │ AgentConsole       │  │  └───────────────┬─────────────────┘    │
│  │ Chat               │  │                  │                       │
│  │ EventTimeline      │  │  ┌───────────────▼─────────────────┐    │
│  │ IterationViewer    │◄─┼──┤       WebSocket /ws              │    │
│  └────────────────────┘  │  └───────────────┬─────────────────┘    │
│      Zustand Store        │                  │                       │
│      useWebSocket()       │  ┌───────────────▼─────────────────┐    │
└──────────────────────────┘  │       Agent Runner               │    │
                              │  StateMachine → Planner          │    │
                              │  → Tools → Memory → EventBus     │    │
                              └───────────────┬─────────────────┘    │
                                              │                       │
                         ┌────────────────────▼──────────────────┐   │
                         │           Self-Extension               │   │
                         │  CapabilityDetector → ToolGenerator    │   │
                         │  SkillGenerator → Sandbox → SelfImprove│  │
                         └────────────────────┬──────────────────┘   │
                                              │                       │
                         ┌────────────────────▼──────────────────┐   │
                         │        Storage Layer (SQLAlchemy)      │   │
                         │  Agent │ Iteration │ Memory │ Tool     │   │
                         │  GitAction │ GeneratedTool │ Skill     │   │
                         └────────────────────┬──────────────────┘   │
                                              │                       │
                              ┌───────────────▼──────┐               │
                              │    Ollama LLM API     │               │
                              │  (qwen2.5-coder, etc) │               │
                              └──────────────────────┘               │
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.ai) running locally with at least one model

### 1. Backend

```bash
cd vertigo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Initialize database
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### 2. Pull a model

```bash
ollama pull qwen2.5-coder:latest
```

### 3. React UI

```bash
cd ui
npm install
npm run dev
# Opens at http://localhost:5173
```

### 4. Docker (optional)

```bash
docker compose up --build
# Backend: http://localhost:8000
# UI: http://localhost:5173
```

## Configuration

Environment variables (`.env` file or shell):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./aaos.db` | SQLAlchemy async DB URL |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_DEFAULT_MODEL` | `qwen2.5-coder:latest` | Default LLM model |
| `OLLAMA_TIMEOUT` | `120` | Request timeout (seconds) |
| `AGENT_MAX_ITERATIONS` | `1000` | Hard cap on iterations per run |
| `AGENT_ITERATION_DELAY` | `1.0` | Seconds between iterations |
| `WORKSPACE_ROOT` | `./workspace` | Sandboxed filesystem root |
| `SECRET_KEY` | change me | JWT signing key |
| `LOG_LEVEL` | `INFO` | Log verbosity |

## API Endpoint Reference

### Agents

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/agents` | Create agent |
| `GET` | `/api/v1/agents` | List all agents (filter by `?state=`) |
| `GET` | `/api/v1/agents/{id}` | Get agent + live status |
| `PATCH` | `/api/v1/agents/{id}` | Update masterprompt / model |
| `DELETE` | `/api/v1/agents/{id}` | Delete agent and all data |
| `POST` | `/api/v1/agents/{id}/start` | Start autonomous loop |
| `POST` | `/api/v1/agents/{id}/pause` | Pause between iterations |
| `POST` | `/api/v1/agents/{id}/resume` | Resume paused agent |
| `POST` | `/api/v1/agents/{id}/stop` | Stop agent |
| `POST` | `/api/v1/agents/{id}/chat` | Chat with agent |
| `GET` | `/api/v1/agents/{id}/iterations` | List iterations |
| `GET` | `/api/v1/agents/{id}/events` | List stored events |

### Memory

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/agents/{id}/memory` | List memory entries |
| `GET` | `/api/v1/agents/{id}/memory/stats` | Count by type |

### Tools

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/tools` | List all registered tools |
| `GET` | `/api/v1/tools/{name}` | Get tool schema |
| `POST` | `/api/v1/tools/execute` | Execute tool directly |

### Models

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/models` | List Ollama models |
| `GET` | `/api/v1/models/health` | Ollama health check |
| `POST` | `/api/v1/models/pull` | Pull model (NDJSON stream) |
| `GET` | `/api/v1/models/{name}/info` | Model details |

### WebSocket

| Path | Description |
|---|---|
| `ws://host/ws` | Live event stream (all agents) |

## Built-in Tools

| Tool | Category | Description |
|---|---|---|
| `read_file` | filesystem | Read file contents |
| `write_file` | filesystem | Write/create file |
| `list_directory` | filesystem | List directory contents |
| `run_command` | execution | Run allowed shell commands |
| `git_status` | git | Current git status |
| `git_commit` | git | Stage and commit changes |
| `git_diff` | git | Show diff |
| `search_code` | search | Search codebase with regex |
| `run_tests` | testing | Execute pytest suite |
| `ollama_generate` | llm | Direct LLM generation |
| `memory_store` | memory | Store to agent memory |
| `memory_recall` | memory | Recall from agent memory |

## Built-in Skills

| Skill | Description |
|---|---|
| `coding` | Full TDD coding loop |
| `debug` | Systematic debugging |
| `refactor` | Safe code refactoring |
| `documentation` | Generate/update docs |
| `git_workflow` | Branch, commit, PR workflow |
| `testing` | Comprehensive test suite writing |
| `planning` | Goal decomposition |
| `memory_management` | Compress and organize memory |

## Example Masterprompts

### General Purpose Coding Agent

```
You are an expert software engineer. Your workspace is /workspace.
For every task:
1. Read existing code before modifying anything
2. Write tests before implementing features (TDD)
3. Run tests after every change
4. Commit working changes with git
5. Update documentation when you change interfaces

Never delete files without explicit instruction.
Always explain what you changed and why.
```

### Research + Summary Agent

```
You are a research assistant. Your goal is to deeply investigate topics,
synthesize information from multiple angles, and produce structured reports.

For each research task:
1. Break the topic into 3-5 sub-questions
2. Investigate each sub-question thoroughly
3. Note confidence levels for each finding
4. Store key facts in long-term memory
5. Produce a final report in markdown
```

### Autonomous Refactoring Agent

```
You are a refactoring specialist. Your job is to incrementally improve
code quality without breaking functionality.

Rules:
- Run the full test suite before and after every change
- Only refactor one concern at a time
- Commit after each successful refactoring
- If tests fail after a change, revert and try a different approach
- Focus on: naming clarity, function length, duplication, complexity
```

## Development Guide

### Project Structure

```
vertigo/
├── app/                   # FastAPI backend
│   ├── api/               # REST routes + WebSocket
│   ├── agent/             # Runner, planner, factory
│   ├── core/              # State machine, events, exceptions
│   ├── database/          # SQLAlchemy models + migrations
│   ├── extensions/        # Self-extension system
│   ├── integrations/      # Ollama, Git clients
│   ├── skills/            # Built-in skill implementations
│   ├── storage/           # Repository pattern
│   └── tools/             # Built-in tool implementations
├── ui/                    # React + Vite + TypeScript frontend
│   └── src/
│       ├── api/           # Axios API clients
│       ├── components/    # React components
│       ├── hooks/         # Custom React hooks
│       ├── pages/         # Route-level components
│       ├── store/         # Zustand global state
│       └── types/         # TypeScript types
├── tests/                 # Pytest test suite
│   ├── unit/              # State machine, events, memory, tools
│   ├── integration/       # Ollama client, agent runner
│   └── e2e/               # Full API tests
└── docs/                  # Detailed documentation
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Unit only
pytest tests/unit/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

### Adding a Custom Tool

1. Create `app/tools/my_tool.py`:

```python
from app.tools.base import BaseTool, ToolResult
from typing import Any

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"
    category = "custom"

    async def execute(self, param: str = "", **kwargs: Any) -> ToolResult:
        try:
            result = f"processed: {param}"
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

2. Register in `app/tools/__init__.py`:

```python
from app.tools.my_tool import MyTool
tool_registry.register(MyTool())
```

### Adding a Custom Skill

```python
from app.skills.base import BaseSkill, SkillResult
from typing import Any, Dict

class MySkill(BaseSkill):
    name = "my_skill"
    description = "Multi-step skill"

    async def execute(self, context: Dict[str, Any]) -> SkillResult:
        # Orchestrate multiple tool calls
        return SkillResult(success=True, output="done")
```

## License

MIT
