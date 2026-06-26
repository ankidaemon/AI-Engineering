"""
Parallel specialist execution (Section 5.2).

When you know up front which analyses a document needs and they are independent,
running them one after another wastes time. `RunnableParallel` fires the
specialists simultaneously and collects their results together. The trade-off is
the mirror image of the supervisor's: parallel is faster but fixed — it cannot
adapt the set of specialists to what it discovers along the way.
"""
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda, RunnableParallel

from src.agents.react_agent import run_agent


def build_parallel_analysis_pipeline(legal_agent, technical_agent, financial_agent):
    def invoke_if(agent, *applicable_types):
        def run(inputs: dict) -> str:
            if inputs.get("doc_type") not in (*applicable_types, "general", "mixed"):
                return ""
            return run_agent(agent, inputs["query"])
        return RunnableLambda(run)

    return RunnableParallel(
        legal_analysis=invoke_if(legal_agent, "legal"),
        technical_analysis=invoke_if(technical_agent, "technical"),
        financial_analysis=invoke_if(financial_agent, "financial"),
    )
