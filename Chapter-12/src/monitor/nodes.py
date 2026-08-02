"""
The nodes of the intelligence pipeline.

Each node is a plain function that takes the state and returns the keys it
changed. The two nodes that call a model (relevance and analysis) build their
chain from a model that is passed in, so tests can inject a fake chat model and
run the whole pipeline with no Ollama server.

`make_nodes(fast_model, quality_model)` returns the node callables wired to the
models you give it. `build_intelligence_graph` in graph.py uses it.
"""
import logging
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

logger = logging.getLogger(__name__)


class RelevanceCheck(BaseModel):
    relevance_score: float = Field(description="0.0 to 1.0 relevance to the topic")
    content_type: str = Field(description="news | research | blog | official | social | other")
    is_relevant: bool = Field(description="True if relevance_score >= 0.6")
    skip_reason: str = Field(description="Why to skip if not relevant, empty otherwise")


class ContentAnalysis(BaseModel):
    key_developments: list = Field(description="New facts or events not already known")
    impact_assessment: str = Field(description="Why this matters to the topic")
    entities: list = Field(description="Key people, organisations, products mentioned")
    sentiment: str = Field(description="positive | negative | neutral")
    urgency: str = Field(description="low | medium | high | breaking")
    action_items: list = Field(description="Recommended actions from this intelligence")


def make_nodes(fast_model, quality_model):
    relevance_parser = JsonOutputParser(pydantic_object=RelevanceCheck)
    relevance_prompt = ChatPromptTemplate.from_messages([
        ("system", "Assess how relevant this content is to the monitored topic. {format_instructions}"),
        ("human", "Topic: {topic}\n\nTitle: {title}\n\nExcerpt:\n{excerpt}"),
    ]).partial(format_instructions=relevance_parser.get_format_instructions())

    analysis_parser = JsonOutputParser(pydantic_object=ContentAnalysis)
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an intelligence analyst. Analyse this content against the topic. "
         "Focus on genuinely new developments not already in the past intelligence. "
         "{format_instructions}"),
        ("human",
         "Topic: {topic}\n\nPast intelligence:\n{past_context}\n\n"
         "New content:\nTitle: {title}\n\n{content}"),
    ]).partial(format_instructions=analysis_parser.get_format_instructions())

    def check_relevance(state: dict) -> dict:
        topic = state.get("topic", "general")
        title = state.get("content_title", "Untitled")
        excerpt = " ".join(state.get("content_text", "").split()[:500])
        try:
            chain = relevance_prompt | fast_model | relevance_parser
            result = chain.invoke({"topic": topic, "title": title, "excerpt": excerpt})
            return {
                "relevance_score": result.get("relevance_score", 0.0),
                "content_type": result.get("content_type", "other"),
                "is_relevant": result.get("is_relevant", False),
                "skip_reason": result.get("skip_reason", ""),
                "current_step": "check_relevance",
                "messages": [AIMessage(content=f"Relevance {result.get('relevance_score', 0):.0%}")],
            }
        except Exception as exc:
            logger.error("Relevance check failed: %s", exc)
            # Fail open: analyse uncertain content rather than dropping it silently.
            return {"is_relevant": True, "skip_reason": "", "current_step": "check_relevance",
                    "errors": [str(exc)]}

    def analyze_content(state: dict) -> dict:
        if not state.get("is_relevant"):
            return {"current_step": "analyze_content"}
        past = state.get("related_past_intel", [])
        past_ctx = "\n".join(past) if past else "No previous intelligence on this topic."
        try:
            chain = analysis_prompt | quality_model | analysis_parser
            result = chain.invoke({
                "topic": state.get("topic", ""),
                "past_context": past_ctx,
                "title": state.get("content_title", ""),
                "content": state.get("content_text", "")[:4000],
            })
            return {
                "key_developments": result.get("key_developments", []),
                "impact_assessment": result.get("impact_assessment", ""),
                "entities": result.get("entities", []),
                "sentiment": result.get("sentiment", "neutral"),
                "urgency": result.get("urgency", "low"),
                "action_items": result.get("action_items", []),
                "current_step": "analyze_content",
                "messages": [AIMessage(content=f"{len(result.get('key_developments', []))} developments")],
            }
        except Exception as exc:
            logger.error("Content analysis failed: %s", exc)
            return {"errors": [*state.get("errors", []), str(exc)], "current_step": "analyze_content"}

    def generate_brief(state: dict) -> dict:
        if not state.get("is_relevant") or not state.get("key_developments"):
            return {"intelligence_brief": "", "current_step": "generate_brief",
                    "skip_reason": state.get("skip_reason") or "No new developments"}
        badge = {"breaking": "BREAKING", "high": "HIGH PRIORITY",
                 "medium": "NOTABLE", "low": "FYI"}.get(state.get("urgency", "low"), "FYI")
        # Model-generated text can contain braces, so it goes in as template
        # values (which are inserted literally), never baked into the template
        # string (which would be parsed for {variables} and could crash).
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Write a concise, specific, actionable intelligence brief in markdown. "
                       "Every sentence must add information."),
            ("human",
             "Badge: {badge}\nTopic: {topic}\nSource: {source}\n"
             "Key developments:\n{developments}\n\nImpact: {impact}\n"
             "Action items:\n{actions}"),
        ])
        brief = (prompt | quality_model | StrOutputParser()).invoke({
            "badge": badge,
            "topic": state.get("topic", ""),
            "source": f"{state.get('content_title', '')} ({state.get('content_url', '')})",
            "developments": "\n".join(f"- {d}" for d in state.get("key_developments", [])),
            "impact": state.get("impact_assessment", ""),
            "actions": "\n".join(f"- {a}" for a in state.get("action_items", [])),
        })
        return {"intelligence_brief": brief, "current_step": "generate_brief",
                "messages": [AIMessage(content=brief[:200])]}

    return check_relevance, analyze_content, generate_brief
