"""
ReAct agent — reason + act in a loop (Chapter 11, Section I).

The loop is: agent → (tools → agent)* → end. The agent node lets the model either
call tools or give a final answer; the router sends it to the tool node or to the
end. The one line that turns this from a demo into something deployable is the
hard cap: `_react_route` checks `tool_calls_made` BEFORE honoring a tool call, so
once the budget is spent the loop ends no matter what the model wants (Failure 1).
"""
import logging

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode

from src.config import settings
from src.state import AgentState

logger = logging.getLogger(__name__)


def _react_route(state: AgentState, max_tool_calls: int) -> str:
    """Pure routing logic — safety cap first, then honor any tool call. Testable."""
    if state.get("tool_calls_made", 0) >= max_tool_calls:
        return "end"                          # hard limit — the model gets no vote
    messages = state.get("messages") or []
    if not messages:
        return "end"
    return "tools" if getattr(messages[-1], "tool_calls", None) else "end"


def build_react_agent(tools, model_name: str | None = None, max_tool_calls: int = 10):
    # bind_tools teaches the model what it may call and what arguments to pass.
    model = ChatOllama(
        model=model_name or settings.quality_model,
        base_url=settings.ollama_base_url,
        temperature=0.0,                      # tool choice wants consistency
    ).bind_tools(tools)

    def agent_node(state: AgentState) -> dict:
        response = model.invoke(state["messages"])
        made = state.get("tool_calls_made", 0)
        if getattr(response, "tool_calls", None):
            made += len(response.tool_calls)
        return {"messages": [response], "tool_calls_made": made}

    def route(state: AgentState) -> str:
        return _react_route(state, max_tool_calls)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")          # after tools, always reconsider
    return graph.compile()


def run_agent(agent, query: str, system_prompt: str = "") -> str:
    """Run an agent on a query and return its final answer."""
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=query))

    result = agent.invoke({"messages": messages, "tool_calls_made": 0})
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            return msg.content
    return "Agent did not produce a final answer."
