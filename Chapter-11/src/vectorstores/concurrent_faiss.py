"""
Thread-safe FAISS wrapper (Chapter 11, Failure 2).

FAISS is read-safe but write-unsafe: two concurrent writers both read the index,
add their documents, and save — and the second save overwrites the first, losing
data silently. The fix is to serialize writes behind a lock while leaving reads
(which are safe) unlocked. For very high write throughput, route all writes
through a single queue with one writer instead.
"""
import threading

from src.vectorstores.faiss_store import FAISSVectorStore


class ThreadSafeFAISSStore:
    def __init__(self, *args, **kwargs):
        self._store = FAISSVectorStore(*args, **kwargs)
        self._lock = threading.Lock()

    def add_documents(self, documents: list) -> int:
        with self._lock:                       # writes are serialized
            return self._store.add_documents(documents)

    def similarity_search(self, *args, **kwargs):
        return self._store.similarity_search(*args, **kwargs)     # reads need no lock

    def similarity_search_with_score(self, *args, **kwargs):
        return self._store.similarity_search_with_score(*args, **kwargs)

    def as_retriever(self, *args, **kwargs):
        return self._store.as_retriever(*args, **kwargs)

    def get_vector_count(self) -> int:
        return self._store.get_vector_count()
