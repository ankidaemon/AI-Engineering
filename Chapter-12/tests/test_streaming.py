"""SSE formatting and the streaming handler, both driven by fakes."""
import json
from src.streaming.stream_handler import sse_event, StreamingResponseHandler


def test_sse_event_shape():
    line = sse_event("token", content="hi")
    assert line.startswith("data: ")
    assert line.endswith("\n\n")
    assert json.loads(line[6:].strip()) == {"type": "token", "content": "hi"}


class FakeState:
    def __init__(self, values):
        self.values = values


class FakeGraph:
    """A stand-in graph: yields two node updates, then holds a finished brief."""
    def stream(self, state, config, stream_mode="updates"):
        yield {"check_relevance": {"current_step": "check_relevance"}}
        yield {"analyze_content": {"current_step": "analyze_content"}}
        yield {"generate_brief": {"current_step": "generate_brief"}}

    def get_state(self, config):
        return FakeState({"intelligence_brief": "hello there world"})


async def test_handler_emits_progress_then_tokens_then_done():
    handler = StreamingResponseHandler(FakeGraph())
    events = [json.loads(line[6:].strip()) async for line in handler.stream({}, {})]

    types = [e["type"] for e in events]
    assert types.count("progress") == 2          # generate_brief is excluded from progress
    assert types.count("token") == 3             # three words in the brief
    assert types[-1] == "done"
    tokens = "".join(e["content"] for e in events if e["type"] == "token")
    assert tokens.strip() == "hello there world"
