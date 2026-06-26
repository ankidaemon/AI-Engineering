"""
Plan-and-execute agent (Section 1.5).

For a *known* multi-step task, deciding everything one step at a time (pure ReAct)
risks losing the thread. Here a planner writes an explicit, ordered list of steps
first; an executor works through them carrying results forward; a synthesize step
combines them. Because the plan is a visible artifact, we can validate it for
internal consistency BEFORE any expensive step runs (`validate_plan`, Failure 5).
"""
from typing import List

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from src.config import settings
from src.state import PlanExecuteState


class ExecutionPlan(BaseModel):
    steps: List[str] = Field(description="Ordered list of steps to complete the task")
    estimated_tools: List[str] = Field(default_factory=list,
                                       description="Tools likely needed")


def validate_plan(plan: List[str], task: str, model) -> tuple[List[str], List[str]]:
    """
    Review a plan for internal consistency before execution.
    Returns (plan, warnings). Does not auto-edit — surfaces conflicts for the
    orchestrator to decide whether to re-plan.
    """
    plan_text = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    response = model.invoke([HumanMessage(content=(
        f"Review this plan for the task: {task}\n\nPlan:\n{plan_text}\n\n"
        f"Identify any steps that (1) contradict each other, (2) make incompatible "
        f"assumptions, or (3) duplicate earlier work. If the plan is consistent, "
        f"reply with exactly: CONSISTENT. Otherwise list the conflicts."
    ))])
    if "CONSISTENT" in response.content.upper():
        return plan, []
    return plan, [response.content]


def build_plan_execute_agent(tools, model_name: str | None = None):
    model = ChatOllama(model=model_name or settings.quality_model,
                       base_url=settings.ollama_base_url, temperature=0.1)
    model_tools = model.bind_tools(tools)
    plan_parser = JsonOutputParser(pydantic_object=ExecutionPlan)

    plan_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a planning agent. Break the task into concrete, sequential steps, "
         "each achievable with a single tool call or reasoning step. "
         "{format_instructions}"),
        ("human", "Task: {task}"),
    ])

    def planner(state: PlanExecuteState) -> dict:
        chain = (
            plan_prompt.partial(format_instructions=plan_parser.get_format_instructions())
            | model
            | plan_parser
        )
        result = chain.invoke({"task": state["task"]})
        return {"plan": result.get("steps", [state["task"]]),
                "current_step": 0, "step_results": {}, "completed_steps": []}

    def executor(state: PlanExecuteState) -> dict:
        plan = state.get("plan", [])
        idx = state.get("current_step", 0)
        if idx >= len(plan):
            return synthesize(state)

        step = plan[idx]
        context = "\n".join(
            f"Step '{s}' result: {str(r)[:500]}"
            for s, r in state.get("step_results", {}).items()
        )
        prompt = (
            f"Overall task: {state['task']}\n\nPrevious results:\n{context}\n\n"
            f"Current step: {step}\n\nUse the available tools to complete this step, "
            f"or reason through it directly if no tool is needed."
        )
        response = model_tools.invoke([HumanMessage(content=prompt)])
        return {"messages": [response], "current_step": idx + 1,
                "completed_steps": [*state.get("completed_steps", []), step]}

    def synthesize(state: PlanExecuteState) -> dict:
        results = "\n".join(
            f"Step {i + 1}: {s}\nResult: {str(r)[:600]}"
            for i, (s, r) in enumerate(state.get("step_results", {}).items())
        )
        prompt = (f"Task: {state['task']}\n\nAll steps completed:\n{results}\n\n"
                  f"Synthesize the results into a final, comprehensive answer.")
        response = model.invoke([HumanMessage(content=prompt)])
        return {"final_answer": response.content, "messages": [response]}

    def route_executor(state: PlanExecuteState) -> str:
        msgs = state.get("messages") or []
        if msgs and getattr(msgs[-1], "tool_calls", None):
            return "tools"
        if state.get("current_step", 0) >= len(state.get("plan", [])):
            return "end"
        return "execute"

    graph = StateGraph(PlanExecuteState)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor", route_executor,
        {"tools": "tools", "execute": "executor", "end": END},
    )
    graph.add_edge("tools", "executor")
    return graph.compile()
