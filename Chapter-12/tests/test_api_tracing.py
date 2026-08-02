"""
The config the API attaches to every pipeline run.

Tagging is the difference between a project full of runs called `LangGraph` and
one you can filter by topic months later, so it is worth a test. No server, no
LangSmith: `run_config` is a plain function.
"""
import pytest

from src.api import run_config, topic_slug


@pytest.mark.parametrize("topic,expected", [
    ("AI regulation", "ai-regulation"),
    ("semiconductor supply chain", "semiconductor-supply-chain"),
    ("  Cyber Threats!  ", "cyber-threats"),
    ("C++", "c"),
    ("!!!", "unknown"),
])
def test_topic_slug(topic, expected):
    assert topic_slug(topic) == expected


def test_run_config_carries_thread_name_tags_and_metadata():
    cfg = run_config("conv-1", "acme", "AI regulation", "https://example.org/act")

    # the checkpointer still gets what it needs, and nothing else
    assert cfg["configurable"] == {"thread_id": "conv-1"}
    # and LangSmith gets a readable name, filterable tags, and traceable metadata
    assert cfg["run_name"] == "intel::AI regulation"
    assert set(cfg["tags"]) == {"chapter-12", "topic:ai-regulation", "customer:acme"}
    assert cfg["metadata"] == {
        "conversation_id": "conv-1",
        "customer_id": "acme",
        "topic": "AI regulation",
        "content_url": "https://example.org/act",
    }


def test_runs_on_the_same_topic_share_a_tag_but_not_a_thread():
    a = run_config("conv-a", "acme", "cyber threats", "https://example.org/1")
    b = run_config("conv-b", "acme", "cyber threats", "https://example.org/2")

    assert a["tags"] == b["tags"]
    assert a["configurable"]["thread_id"] != b["configurable"]["thread_id"]


def test_two_customers_on_one_topic_are_told_apart_by_tag():
    """So a support question about one customer's runs is a filter, not a scan."""
    acme = run_config("conv-a", "acme", "cyber threats", "https://example.org/1")
    globex = run_config("conv-b", "globex", "cyber threats", "https://example.org/1")

    assert "customer:acme" in acme["tags"]
    assert "customer:globex" in globex["tags"]
    assert acme["metadata"]["customer_id"] != globex["metadata"]["customer_id"]
