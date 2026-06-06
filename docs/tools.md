# Tool Reference

Tools are atomic capabilities the agent can invoke during iterations.

## Filesystem Tools

### `read_file`
Read the contents of a file.

| Arg | Type | Description |
|---|---|---|
| `path` | string | Absolute or workspace-relative path |
| `start_line` | int? | First line (1-indexed) |
| `end_line` | int? | Last line inclusive |

### `write_file`
Write or overwrite a file.

| Arg | Type | Description |
|---|---|---|
| `path` | string | File path (must be under WORKSPACE_ROOT) |
| `content` | string | Full file content |
| `create_dirs` | bool | Create parent directories if missing |

### `list_directory`
List directory contents.

| Arg | Type | Description |
|---|---|---|
| `path` | string | Directory path |
| `recursive` | bool | Include subdirectories |
| `pattern` | string? | Glob pattern filter |

## Execution Tools

### `run_command`
Execute an allowlisted shell command.

| Arg | Type | Description |
|---|---|---|
| `command` | string | Command to run |
| `cwd` | string? | Working directory |
| `timeout` | int | Timeout in seconds (default 60) |

Allowed commands: `python`, `pip`, `npm`, `node`, `git`, `pytest`, `black`, `ruff`, `mypy`

## Git Tools

### `git_status`
Return current git status.

### `git_commit`
Stage all changes and commit.

| Arg | Type | Description |
|---|---|---|
| `message` | string | Commit message |
| `add_all` | bool | Stage all modified files |

### `git_diff`
Show current diff.

| Arg | Type | Description |
|---|---|---|
| `staged` | bool | Show staged diff only |
| `file` | string? | Specific file |

## Search Tools

### `search_code`
Search codebase with regex.

| Arg | Type | Description |
|---|---|---|
| `pattern` | string | Regex pattern |
| `path` | string | Search root |
| `file_glob` | string? | File pattern (e.g., `*.py`) |

## Testing Tools

### `run_tests`
Execute pytest.

| Arg | Type | Description |
|---|---|---|
| `path` | string | Test path or file |
| `args` | list? | Extra pytest args |
| `timeout` | int | Timeout seconds |

## Memory Tools

### `memory_store`
Store a key-value pair in memory.

| Arg | Type | Description |
|---|---|---|
| `key` | string | Memory key |
| `content` | string | Content to store |
| `memory_type` | string | `short`, `mid`, or `long` |

### `memory_recall`
Retrieve from memory by key.

| Arg | Type | Description |
|---|---|---|
| `key` | string | Memory key |
| `fuzzy` | bool | Enable fuzzy search |

## LLM Tools

### `ollama_generate`
Direct LLM generation bypass (for sub-agents, summarization, etc.)

| Arg | Type | Description |
|---|---|---|
| `prompt` | string | Prompt text |
| `model` | string? | Override model |
| `system` | string? | System message |

## Writing Custom Tools

```python
from app.tools.base import BaseTool, ToolResult, ToolPermission
from typing import Any

class MyTool(BaseTool):
    name = "my_tool"
    description = "One-line description for the LLM"
    category = "custom"
    permissions = [ToolPermission.READ]

    async def execute(self, arg1: str, arg2: int = 0, **kwargs: Any) -> ToolResult:
        try:
            result = do_something(arg1, arg2)
            return ToolResult(success=True, output=str(result))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def get_schema(self) -> dict:
        schema = super().get_schema()
        schema["input_schema"] = {
            "type": "object",
            "properties": {
                "arg1": {"type": "string", "description": "..."},
                "arg2": {"type": "integer", "description": "..."},
            },
            "required": ["arg1"],
        }
        return schema
```

Register in `app/tools/__init__.py`:

```python
from app.tools.my_tool import MyTool
tool_registry.register(MyTool())
```
