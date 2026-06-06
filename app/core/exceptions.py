from typing import Optional, Any, Dict


class AAOSException(Exception):
    """Base exception for all AAOS errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.__class__.__name__, "message": self.message, "details": self.details}


class AgentNotFoundError(AAOSException):
    """Raised when an agent cannot be found."""


class AgentStateError(AAOSException):
    """Raised when an invalid state transition is attempted."""


class InvalidTransitionError(AgentStateError):
    """Raised when the transition is not allowed by the state machine."""


class ToolExecutionError(AAOSException):
    """Raised when a tool fails during execution."""


class ToolNotFoundError(AAOSException):
    """Raised when a requested tool does not exist."""


class ToolPermissionError(AAOSException):
    """Raised when a tool lacks the required permission."""


class MemoryError(AAOSException):
    """Raised on memory subsystem failures."""


class OllamaConnectionError(AAOSException):
    """Raised when the Ollama service is unreachable."""


class OllamaModelError(AAOSException):
    """Raised when a model operation fails."""


class GitOperationError(AAOSException):
    """Raised when a git operation fails."""


class GitConfirmationRequired(AAOSException):
    """Raised when a destructive git action needs user confirmation."""


class PlanningError(AAOSException):
    """Raised when the planner cannot produce a valid plan."""


class SkillExecutionError(AAOSException):
    """Raised when a skill fails during execution."""


class WorkspaceSecurityError(AAOSException):
    """Raised when a path traversal or forbidden operation is attempted."""


class DatabaseError(AAOSException):
    """Raised on database-level failures."""


class ValidationError(AAOSException):
    """Raised when input validation fails."""
