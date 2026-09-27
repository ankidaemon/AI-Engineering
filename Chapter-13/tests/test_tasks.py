"""Background tasks, tested as the plain functions they are (§7.3, §8.13)."""
from src.workers.tasks import ingest_batch_impl, reindex_document_impl


class FakePipeline:
    def __init__(self):
        self.replaced = []
        self.index = self

    def load_document(self, doc_id):
        return [f"{doc_id}-doc"]

    def split_and_embed(self, docs):
        return [f"{d}-chunk-{i}" for d in docs for i in range(3)]

    def replace(self, doc_id, chunks):
        self.replaced.append((doc_id, len(chunks)))


def test_reindex_swaps_a_documents_chunks():
    pipeline = FakePipeline()
    result = reindex_document_impl("card-faq", pipeline)
    assert result == {"doc_id": "card-faq", "chunks": 3}
    assert pipeline.replaced == [("card-faq", 3)]


def test_batch_fans_out_one_job_per_document():
    """§7.5: many small jobs, not one giant one — the queue paces them."""
    queued = []
    result = ingest_batch_impl(["fees", "faq", "terms"], enqueue=queued.append)
    assert result == {"queued": 3}
    assert queued == ["fees", "faq", "terms"]


def test_empty_batch_queues_nothing():
    queued = []
    assert ingest_batch_impl([], enqueue=queued.append) == {"queued": 0}
    assert queued == []
