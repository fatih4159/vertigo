"""Unit tests for AgentState machine."""
import pytest
from app.core.state_machine import AgentState, StateMachine


def test_initial_state():
    sm = StateMachine()
    assert sm.state == AgentState.IDLE


def test_idle_to_running():
    sm = StateMachine()
    result = sm.transition(AgentState.RUNNING, reason="start")
    assert result is True
    assert sm.state == AgentState.RUNNING


def test_running_to_paused():
    sm = StateMachine()
    sm.transition(AgentState.RUNNING)
    result = sm.transition(AgentState.PAUSED, reason="user pause")
    assert result is True
    assert sm.state == AgentState.PAUSED


def test_paused_to_running():
    sm = StateMachine()
    sm.transition(AgentState.RUNNING)
    sm.transition(AgentState.PAUSED)
    result = sm.transition(AgentState.RUNNING, reason="resume")
    assert result is True
    assert sm.state == AgentState.RUNNING


def test_running_to_stopped():
    sm = StateMachine()
    sm.transition(AgentState.RUNNING)
    result = sm.transition(AgentState.STOPPED)
    assert result is True
    assert sm.state == AgentState.STOPPED


def test_stopped_to_idle():
    sm = StateMachine()
    sm.transition(AgentState.RUNNING)
    sm.transition(AgentState.STOPPED)
    result = sm.transition(AgentState.IDLE)
    assert result is True
    assert sm.state == AgentState.IDLE


def test_invalid_transition_idle_to_stopped():
    sm = StateMachine()
    result = sm.transition(AgentState.STOPPED)
    assert result is False
    assert sm.state == AgentState.IDLE  # unchanged


def test_invalid_transition_idle_to_paused():
    sm = StateMachine()
    result = sm.transition(AgentState.PAUSED)
    assert result is False
    assert sm.state == AgentState.IDLE


def test_running_to_error():
    sm = StateMachine()
    sm.transition(AgentState.RUNNING)
    result = sm.transition(AgentState.ERROR, reason="tool failure")
    assert result is True
    assert sm.state == AgentState.ERROR


def test_error_to_idle():
    sm = StateMachine()
    sm.transition(AgentState.RUNNING)
    sm.transition(AgentState.ERROR)
    result = sm.transition(AgentState.IDLE)
    assert result is True
    assert sm.state == AgentState.IDLE


def test_can_transition():
    sm = StateMachine()
    assert sm.can_transition(AgentState.RUNNING) is True
    assert sm.can_transition(AgentState.PAUSED) is False


def test_transition_history_recorded():
    sm = StateMachine()
    sm.transition(AgentState.RUNNING, reason="start")
    sm.transition(AgentState.PAUSED, reason="pause")
    assert len(sm.transition_history) == 2
    assert sm.transition_history[0]["from"] == AgentState.IDLE.value
    assert sm.transition_history[0]["to"] == AgentState.RUNNING.value
    assert sm.transition_history[0]["reason"] == "start"


def test_failed_transition_not_in_history():
    sm = StateMachine()
    sm.transition(AgentState.PAUSED)  # invalid
    assert len(sm.transition_history) == 0


def test_previous_state_tracked():
    sm = StateMachine()
    sm.transition(AgentState.RUNNING)
    assert sm.previous_state == AgentState.IDLE
    sm.transition(AgentState.PAUSED)
    assert sm.previous_state == AgentState.RUNNING
