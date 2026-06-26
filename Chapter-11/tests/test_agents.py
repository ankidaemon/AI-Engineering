"""
Agent routing tests. The routing/safety logic is factored into pure functions, so
the most important behaviour — the hard caps that guarantee termination — is
tested directly, with no model server. (See Chapter 11, Failure 1.)
"""
from langchain_core.messages import AIMessage

from src.agents.react_agent import _react_route
from src.agents.reflection_agent import _reflection_route
from src.agents.supervisor_agent import _supervisor_route
from src.agents.plan_execute_agent import validate_plan


def _tool_msg():
    return AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "1"}])


# ── ReAct router ──────────────────────────────────────────────────────

def test_react_routes_to_tools_on_tool_call():
    state = {"messages": [_tool_msg()], "tool_calls_made": 1}
    assert _react_route(state, max_tool_calls=10) == "tools"


def test_react_ends_on_final_answer():
    state = {"messages": [AIMessage(content="final answer")], "tool_calls_made": 1}
    assert _react_route(state, max_tool_calls=10) == "end"


def test_react_hard_cap_overrides_tool_call():
    # Even with a pending tool call, hitting the cap forces termination.
    state = {"messages": [_tool_msg()], "tool_calls_made": 10}
    assert _react_route(state, max_tool_calls=10) == "end"


# ── Reflection router ─────────────────────────────────────────────────

def test_reflection_stops_on_approval():
    state = {"critique": "APPROVED: No revisions needed.", "iteration": 1,
             "max_iterations": 2}
    assert _reflection_route(state) == "end"


def test_reflection_stops_at_iteration_cap():
    state = {"critique": "needs work", "iteration": 2, "max_iterations": 2}
    assert _reflection_route(state) == "end"


def test_reflection_revises_when_unsatisfied():
    state = {"critique": "needs work", "iteration": 1, "max_iterations": 2}
    assert _reflection_route(state) == "revise"


# ── Supervisor router ─────────────────────────────────────────────────

def test_supervisor_finishes_on_finish():
    state = {"supervisor_decision": {"next_agent": "FINISH"}, "iteration": 1}
    assert _supervisor_route(state, max_iter=8) == "end"


def test_supervisor_hard_cap():
    state = {"supervisor_decision": {"next_agent": "legal"}, "iteration": 8}
    assert _supervisor_route(state, max_iter=8) == "end"


def test_supervisor_routes_to_specialist():
    state = {"supervisor_decision": {"next_agent": "legal"}, "iteration": 1}
    assert _supervisor_route(state, max_iter=8) == "legal"


# ── Plan validation (model injected) ──────────────────────────────────

class _FakeResp:
    def __init__(self, content):
        self.content = content


class _FakeModel:
    def __init__(self, content):
        self._content = content

    def invoke(self, _messages):
        return _FakeResp(self._content)


def test_validate_plan_consistent():
    plan, warnings = validate_plan(["a", "b"], "task", _FakeModel("CONSISTENT"))
    assert warnings == []
    assert plan == ["a", "b"]


def test_validate_plan_flags_conflict():
    _, warnings = validate_plan(["a", "b"], "task",
                                _FakeModel("Conflict: step a contradicts step b"))
    assert warnings
