"""
The state passed between nodes of the intelligence pipeline.

Every node reads what it needs from this dict and returns only the keys it
changed. `total=False` means no key is required up front, which lets each node
fill in its own part as the run progresses.
"""
import operator
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage


class IntelligenceState(TypedDict, total=False):
    # Input
    content_url: str
    content_text: str
    content_title: str
    topic: str
    monitor_id: str
    customer_id: str          # set from the authenticated caller, never from the body

    # Classification
    content_type: str
    relevance_score: float
    is_relevant: bool

    # Analysis
    key_developments: list
    impact_assessment: str
    entities: list
    sentiment: str
    urgency: str

    # Context recalled from past intelligence
    related_past_intel: list

    # Output
    intelligence_brief: str
    action_items: list

    # Control
    messages: Annotated[Sequence[BaseMessage], operator.add]
    errors: list
    current_step: str
    skip_reason: Optional[str]
