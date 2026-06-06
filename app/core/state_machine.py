from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime


class AgentState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


VALID_TRANSITIONS: Dict[AgentState, List[AgentState]] = {
    AgentState.IDLE: [AgentState.RUNNING],
    AgentState.RUNNING: [
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.ERROR,
        AgentState.WAITING_FOR_APPROVAL,
    ],
    AgentState.PAUSED: [AgentState.RUNNING, AgentState.STOPPED],
    AgentState.WAITING_FOR_APPROVAL: [
        AgentState.RUNNING,
        AgentState.STOPPED,
        AgentState.PAUSED,
    ],
    AgentState.ERROR: [AgentState.IDLE, AgentState.STOPPED],
    AgentState.STOPPED: [AgentState.IDLE],
}


class StateMachine:
    def __init__(self):
        self.state: AgentState = AgentState.IDLE
        self.previous_state: Optional[AgentState] = None
        self.state_entered_at: datetime = datetime.utcnow()
        self.transition_history: List[Dict[str, Any]] = []

    def can_transition(self, to_state: AgentState) -> bool:
        return to_state in VALID_TRANSITIONS.get(self.state, [])

    def transition(self, to_state: AgentState, reason: str = "") -> bool:
        if not self.can_transition(to_state):
            return False
        self.transition_history.append(
            {
                "from": self.state.value,
                "to": to_state.value,
                "reason": reason,
                "at": datetime.utcnow().isoformat(),
            }
        )
        if len(self.transition_history) > 500:
            self.transition_history = self.transition_history[-500:]
        self.previous_state = self.state
        self.state = to_state
        self.state_entered_at = datetime.utcnow()
        return True

    def force_transition(self, to_state: AgentState, reason: str = "") -> None:
        """Force a transition regardless of validity (admin use only)."""
        self.transition_history.append(
            {
                "from": self.state.value,
                "to": to_state.value,
                "reason": f"[FORCED] {reason}",
                "at": datetime.utcnow().isoformat(),
            }
        )
        self.previous_state = self.state
        self.state = to_state
        self.state_entered_at = datetime.utcnow()

    def is_running(self) -> bool:
        return self.state == AgentState.RUNNING

    def is_paused(self) -> bool:
        return self.state == AgentState.PAUSED

    def is_stopped(self) -> bool:
        return self.state == AgentState.STOPPED

    def is_waiting(self) -> bool:
        return self.state == AgentState.WAITING_FOR_APPROVAL

    def is_error(self) -> bool:
        return self.state == AgentState.ERROR

    def is_idle(self) -> bool:
        return self.state == AgentState.IDLE

    def seconds_in_current_state(self) -> float:
        return (datetime.utcnow() - self.state_entered_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "state_entered_at": self.state_entered_at.isoformat(),
            "seconds_in_state": self.seconds_in_current_state(),
            "transition_count": len(self.transition_history),
        }
