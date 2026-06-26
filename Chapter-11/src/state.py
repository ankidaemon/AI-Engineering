"""
Typed state shapes for the agents in this chapter.

Each agent is a LangGraph workflow, and LangGraph threads a typed dictionary
through its nodes. The `messages` field uses the `operator.add` reducer so that
each node *appends* to the running transcript instead of overwriting it (the
standard pattern introduced in Chapter 10).
"""
import operator
from typing import TypedDict, Annotated, Sequence, List

from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """State for the ReAct agent (Section I)."""
    messages:        Annotated[Sequence[BaseMessage], operator.add]
    tool_calls_made: int          # safety counter — drives the hard cap
    final_answer:    str


class ReflectionState(TypedDict, total=False):
    """State for the generate → critique → revise loop (Section 1.4)."""
    task:           str
    draft:          str
    critique:       str
    iteration:      int
    max_iterations: int
    messages:       Annotated[Sequence[BaseMessage], operator.add]


class PlanExecuteState(TypedDict, total=False):
    """State for the plan-then-execute agent (Section 1.5)."""
    task:            str
    plan:            List[str]
    completed_steps: List[str]
    current_step:    int
    step_results:    dict
    final_answer:    str
    messages:        Annotated[Sequence[BaseMessage], operator.add]


class MultiAgentState(TypedDict, total=False):
    """State for the supervisor / specialist system (Section V)."""
    document_text:    str
    document_type:    str
    task:             str

    legal_output:     str
    technical_output: str
    financial_output: str

    agents_called:       List[str]
    supervisor_decision: dict
    iteration:           int

    synthesis: str
    messages:  Annotated[Sequence[BaseMessage], operator.add]
