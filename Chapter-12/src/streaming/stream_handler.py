"""
Server-Sent Events (SSE) helpers.

Users read faster than a model generates, so streaming the answer token by token
makes the system feel far quicker even though the total time is the same. SSE is
the simplest transport for this: the server writes `data: ...\\n\\n` lines and the
browser's EventSource reads them as they arrive.

`sse_event` formats one event. `StreamingResponseHandler` walks a LangGraph
stream and turns each update into an SSE line. The formatting is pure text, so
the tests need no server and no model.
"""
import json
from typing import Any, AsyncIterator


def sse_event(event_type: str, **fields: Any) -> str:
    """Format a single SSE line, e.g. sse_event('token', content='hi')."""
    payload = {"type": event_type, **fields}
    return f"data: {json.dumps(payload)}\n\n"


class StreamingResponseHandler:
    """
    Turns a compiled LangGraph into a stream of SSE events. Progress events are
    emitted as each node finishes; token events carry the generated brief.
    """

    def __init__(self, graph, generation_node: str = "generate_brief"):
        self._graph = graph
        self._generation_node = generation_node

    async def stream(self, state: dict, config: dict) -> AsyncIterator[str]:
        # Phase 1: emit a progress event per node as the graph advances.
        for chunk in self._graph.stream(state, config, stream_mode="updates"):
            for node, output in chunk.items():
                if node == self._generation_node:
                    continue
                yield sse_event(
                    "progress",
                    node=node,
                    step=(output or {}).get("current_step", node),
                )

        # Phase 2: emit the finished brief as token events.
        final = self._graph.get_state(config)
        brief = final.values.get("intelligence_brief", "")
        for word in brief.split():
            yield sse_event("token", content=word + " ")

        yield sse_event("done")
