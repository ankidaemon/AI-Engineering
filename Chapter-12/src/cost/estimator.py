"""
Estimate the cost of a request before you spend it.

The `CostTracker` in `observability/tracing.py` records what a call actually
cost after the fact. This module answers the other question: given a prompt I
am about to send, how much will it cost, and what does a month of this traffic
add up to? You need that number before you ship, not after the invoice.
"""
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Prices per one million tokens. Keep in sync with CostTracker.PRICING.
# Self-hosted models cost compute, not tokens, so their per-token price is zero.
PRICING = {
    "llama3.1:8b": {"input": 0.00, "output": 0.00},
    "llama3.1:70b": {"input": 0.00, "output": 0.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 5.00, "output": 15.00},
}


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    Best effort token count. tiktoken is exact for OpenAI models and a close
    estimate for others (their tokenizers differ, but close enough for a
    budget). Falls back to a four characters per token heuristic when tiktoken
    is not installed, so this function never fails.
    """
    try:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


@dataclass
class CostEstimate:
    model: str
    input_tokens: int
    projected_output_tokens: int
    cost_usd: float


def estimate_request_cost(
    prompt: str,
    model: str = "gpt-4o-mini",
    projected_output_tokens: int = 500,
) -> CostEstimate:
    """
    Estimate the cost of one request. `prompt` is the full assembled prompt:
    system text, conversation history, retrieved context and the user message.
    Pass a realistic `projected_output_tokens` (your max_tokens cap is a good
    upper bound).
    """
    price = PRICING.get(model, {"input": 0.0, "output": 0.0})
    input_tokens = count_tokens(prompt, model)
    cost = (
        (input_tokens / 1_000_000) * price["input"]
        + (projected_output_tokens / 1_000_000) * price["output"]
    )
    return CostEstimate(model, input_tokens, projected_output_tokens, round(cost, 6))


def project_monthly_cost(
    requests_per_day: int,
    avg_prompt: str,
    model: str = "gpt-4o-mini",
    projected_output_tokens: int = 500,
) -> float:
    """Capacity planning: what does this traffic cost over thirty days?"""
    per_request = estimate_request_cost(avg_prompt, model, projected_output_tokens)
    monthly = per_request.cost_usd * requests_per_day * 30
    logger.info(
        "Projection: %s req/day at $%.6f each is about $%.2f/month (%s)",
        requests_per_day, per_request.cost_usd, monthly, model,
    )
    return round(monthly, 2)
