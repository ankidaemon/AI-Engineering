"""
Shared fakes: the whole suite runs offline (§8.13).

FakeEmbeddings is a deterministic bag-of-words embedder: tokens hash into a
fixed number of buckets and the vector is normalized, so texts that share
words land close together. That is enough signal for every retrieval test
without a model server. FakeModel records the prompts it was given and
returns scripted replies, so tests can assert both what the model was asked
and how its answer was used.
"""
import math
import re
import zlib
from types import SimpleNamespace

import pytest
from langchain_core.embeddings import Embeddings


class FakeEmbeddings(Embeddings):
    DIM = 128

    def _embed(self, text: str) -> list:
        vec = [0.0] * self.DIM
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            vec[zlib.crc32(token.encode()) % self.DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_documents(self, texts: list) -> list:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list:
        return self._embed(text)


class FakeModel:
    """reply may be a string, a list of strings (consumed in order), or a
    callable(prompt) -> string."""

    def __init__(self, reply="ok"):
        self._reply = reply
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        if callable(self._reply):
            content = self._reply(prompt)
        elif isinstance(self._reply, list):
            content = self._reply.pop(0)
        else:
            content = self._reply
        return SimpleNamespace(content=content)


@pytest.fixture
def embeddings():
    return FakeEmbeddings()


@pytest.fixture
def fake_redis():
    import fakeredis
    return fakeredis.FakeRedis()
