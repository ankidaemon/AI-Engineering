"""
Supervisor multi-agent system (Section V).

A supervisor repeatedly decides which specialist (legal / technical / financial)
to call next; each specialist does focused work and reports back; a synthesizer
combines everything. This is conditional routing (Chapter 10) raised one level so
the things routed to are whole agents. The hard iteration cap in `_supervisor_route`
guarantees the system terminates — even more important here because each
specialist may itself run a multi-step loop.
"""
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END, START
from pydantic import BaseModel, Field

from src.config import settings
from src.state import MultiAgentState


class SupervisorDecision(BaseModel):
    next_agent: str = Field(
        description="Next agent: legal, technical, financial, synthesize, or FINISH")
    reasoning: str = Field(description="Why this agent is needed next")
    task_for_agent: str = Field(description="Specific instruction for the chosen agent")


_PARSER = JsonOutputParser(pydantic_object=SupervisorDecision)
_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a document-analysis supervisor coordinating specialists. Agents:\n"
     "- 'legal': clauses, obligations, liabilities, risks\n"
     "- 'technical': architecture, security, dependencies\n"
     "- 'financial': financial terms, costs, payment structures\n"
     "- 'synthesize': combine all outputs into a final report\n"
     "- 'FINISH': end the workflow\n\n"
     "Choose based on document type and what is still missing. Call 'synthesize' "
     "only after the relevant specialists have run. {format_instructions}"),
    ("human",
     "Document type: {document_type}\nTask: {task}\n\n"
     "Agents already called: {agents_called}\n\n"
     "Outputs so far:\n{outputs_summary}\n\nWhat should happen next?"),
])


def _supervisor_route(state: MultiAgentState, max_iter: int) -> str:
    """Pure routing logic — finish on FINISH or at the iteration cap. Testable."""
    decision = state.get("supervisor_decision", {})
    next_agent = decision.get("next_agent", "FINISH")
    if state.get("iteration", 0) >= max_iter or next_agent == "FINISH":
        return "end"
    return {"legal": "legal", "technical": "technical",
            "financial": "financial", "synthesize": "synthesize"}.get(next_agent, "end")


def _summarize_outputs(state: MultiAgentState) -> str:
    parts = []
    for kind in ("legal", "technical", "financial"):
        out = state.get(f"{kind}_output")
        if out:
            parts.append(f"{kind.title()}: {out[:300]}...")
    return "\n\n".join(parts) or "No outputs yet"


def build_supervisor_agent(
    legal_agent, technical_agent, financial_agent, synthesizer,
    model_name: str | None = None, max_iter: int = None,
):
    max_iter = max_iter or settings.max_agent_iter
    model = ChatOllama(model=model_name or settings.quality_model,
                       base_url=settings.ollama_base_url, temperature=0)

    def supervisor(state: MultiAgentState) -> dict:
        chain = _PROMPT.partial(
            format_instructions=_PARSER.get_format_instructions()) | model | _PARSER
        decision = chain.invoke({
            "document_type": state.get("document_type", "unknown"),
            "task": state.get("task", "Analyze this document"),
            "agents_called": ", ".join(state.get("agents_called", [])) or "none",
            "outputs_summary": _summarize_outputs(state),
        })
        return {"supervisor_decision": decision,
                "iteration": state.get("iteration", 0) + 1,
                "messages": [AIMessage(content=f"Supervisor → {decision.get('next_agent')}")]}

    def _run(agent, kind):
        def node(state: MultiAgentState) -> dict:
            task = state.get("supervisor_decision", {}).get("task_for_agent", "")
            result = agent.invoke({"task": task, "document": state.get("document_text", "")})
            output = result.get("final_answer", str(result)) if isinstance(result, dict) else str(result)
            return {f"{kind}_output": output,
                    "agents_called": [*state.get("agents_called", []), kind]}
        return node

    def run_synthesizer(state: MultiAgentState) -> dict:
        return {"synthesis": synthesizer(state),
                "agents_called": [*state.get("agents_called", []), "synthesize"]}

    def route(state: MultiAgentState) -> str:
        return _supervisor_route(state, max_iter)

    graph = StateGraph(MultiAgentState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("legal", _run(legal_agent, "legal"))
    graph.add_node("technical", _run(technical_agent, "technical"))
    graph.add_node("financial", _run(financial_agent, "financial"))
    graph.add_node("synthesize", run_synthesizer)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route, {
        "legal": "legal", "technical": "technical", "financial": "financial",
        "synthesize": "synthesize", "end": END,
    })
    for node in ("legal", "technical", "financial", "synthesize"):
        graph.add_edge(node, "supervisor")
    return graph.compile()
