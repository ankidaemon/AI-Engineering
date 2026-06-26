"""
Reflection agent — generate, self-critique, revise (Section 1.4).

A small loop between two nodes: `generate` writes a draft; `critique` reviews it
and either approves it (with the exact phrase 'APPROVED:') or returns actionable
criticism. The router stops on EITHER approval OR an iteration cap, so a critic
that is never quite satisfied still cannot loop forever.
"""
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END, START

from src.config import settings
from src.state import ReflectionState


def _reflection_route(state: ReflectionState) -> Literal["revise", "end"]:
    """Pure routing logic — stop on approval or at the iteration cap. Testable."""
    critique = state.get("critique", "")
    if "APPROVED:" in critique or state.get("iteration", 0) >= state.get("max_iterations", 2):
        return "end"
    return "revise"


def build_reflection_agent(model_name: str | None = None, max_iterations: int = 2):
    model = ChatOllama(
        model=model_name or settings.quality_model,
        base_url=settings.ollama_base_url,
        temperature=0.2,
    )

    def generate_draft(state: ReflectionState) -> dict:
        prior = state.get("critique", "")
        prompt = (
            f"Task: {state['task']}\n\n"
            + (f"Address this critique:\n{prior}\n\n" if prior else "")
            + "Produce a thorough, well-structured analysis."
        )
        response = model.invoke([HumanMessage(content=prompt)])
        return {"draft": response.content, "messages": [response]}

    def critique_draft(state: ReflectionState) -> dict:
        prompt = (
            f"Review this analysis for quality, accuracy, and completeness.\n\n"
            f"{state['draft']}\n\n"
            f"Give specific, actionable critique. If it is already sufficient, "
            f"reply with exactly: 'APPROVED: No revisions needed.'"
        )
        response = model.invoke([HumanMessage(content=prompt)])
        return {
            "critique": response.content,
            "iteration": state.get("iteration", 0) + 1,
            "messages": [response],
        }

    def route(state: ReflectionState) -> str:
        merged = {"max_iterations": max_iterations, **state}
        return _reflection_route(merged)

    graph = StateGraph(ReflectionState)
    graph.add_node("generate", generate_draft)
    graph.add_node("review", critique_draft)   # node name != the 'critique' state key
    graph.add_edge(START, "generate")
    graph.add_edge("generate", "review")
    graph.add_conditional_edges("review", route, {"revise": "generate", "end": END})
    return graph.compile()
