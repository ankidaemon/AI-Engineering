"""
Tool definitions for the action agent (§6.2).

The first and most useful distinction on the action side is between tools
that only READ and tools that CHANGE something. Reads are safe to repeat, so
they can be called generously. Writes may create two of something if run
twice, so they go through extra steps: required-field validation, an
idempotency check, and for high-impact actions a confirmation. Keeping the
two kinds visibly separate is what lets the rules differ.

Every ToolSpec carries a rich plain-language `description`, because that
description is what the retrieval-based selector (§6.4) embeds and searches.
A tool that is described well gets chosen well.
"""
from dataclasses import dataclass, field


@dataclass
class ToolSpec:
    name: str
    description: str              # embedded by the selector — write it richly
    kind: str                     # "read" | "write"
    required_fields: tuple = ()
    # field -> the only values accepted, checked by code before acting
    allowed_values: dict = field(default_factory=dict)
    # the fields that make two requests "the same request" (§6.5);
    # empty means all the required fields
    same_request_fields: tuple = ()
    requires_confirmation: bool = False
    handler: object = None        # callable(fields, desk) -> result


@dataclass
class ActionResult:
    status: str                   # "done" | "needs_info" | "needs_confirmation" | "unknown_tool"
    message: str = ""
    reference: str = ""           # ticket / tracking id the customer keeps (§6.3)
    missing_fields: list = field(default_factory=list)
    duplicate: bool = False       # True when idempotency returned the original
