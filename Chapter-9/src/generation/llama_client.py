import json
import logging
import httpx
from typing import AsyncIterator
from src.config import settings

logger = logging.getLogger(__name__)


class LlamaClient:
    """
    Async client for Llama 3.1 served via Ollama's REST API.

    Ollama exposes an OpenAI-compatible /api/chat endpoint.
    This client handles both batch (standard) and streaming responses.

    Model-specific notes for Llama 3.1:
    - repeat_penalty=1.1 discourages the model from repeating retrieved
      context verbatim, encouraging synthesis over regurgitation.
    - stop tokens include Llama 3.1's special end-of-message token
      (<|eot_id|>) to prevent runaway generation.
    - temperature=0.1 is appropriate for factual RAG tasks where
      creativity is less important than accuracy and consistency.
    """

    def __init__(self):
        self._model = settings.llama_model
        self._base_url = settings.ollama_base_url

    async def generate(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None
    ) -> str:
        payload = {
            "model":    self._model,
            "messages": messages,
            "stream":   False,
            "options": {
                "temperature":    temperature or settings.llama_temperature,
                "num_predict":    max_tokens or settings.llama_max_tokens,
                "top_p":          0.92,
                "repeat_penalty": 1.1,
                "stop":           ["<|eot_id|>", "<|end_of_text|>"]
            }
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

    async def stream(
        self,
        messages: list[dict],
        temperature: float | None = None
    ) -> AsyncIterator[str]:
        """
        Yields token strings as they arrive from Ollama.
        Use this for streaming responses to the client.
        """
        payload = {
            "model":    self._model,
            "messages": messages,
            "stream":   True,
            "options": {
                "temperature":    temperature or settings.llama_temperature,
                "num_predict":    settings.llama_max_tokens,
                "top_p":          0.92,
                "repeat_penalty": 1.1,
                "stop":           ["<|eot_id|>", "<|end_of_text|>"]
            }
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if content := chunk.get("message", {}).get("content", ""):
                        yield content
                    if chunk.get("done"):
                        break

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
