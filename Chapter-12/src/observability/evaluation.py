"""
Evaluation datasets and evaluators.

A dataset is a set of inputs paired with the answer you expect. You build it
from real traffic: every time a user gets a good answer, that becomes a data
point. Then you re-run the system against the whole set before every change to
catch quality regressions before users do.

The evaluators here are ordinary functions that return a score between zero and
one, so they are trivial to unit test. `EvaluationDatasetManager` wraps the
LangSmith dataset API and takes an injected client for offline tests.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Evaluators (pure functions, score in [0, 1]) ─────────────────────

def exact_match(prediction: str, reference: str) -> float:
    return 1.0 if prediction.strip().lower() == reference.strip().lower() else 0.0


def contains_reference(prediction: str, reference: str) -> float:
    return 1.0 if reference.strip().lower() in prediction.strip().lower() else 0.0


def keyword_recall(prediction: str, keywords: list) -> float:
    """Fraction of expected keywords that appear in the prediction."""
    if not keywords:
        return 1.0
    text = prediction.lower()
    hit = sum(1 for kw in keywords if kw.lower() in text)
    return hit / len(keywords)


# ── Dataset management ───────────────────────────────────────────────

class EvaluationDatasetManager:
    """Create and grow a LangSmith evaluation dataset. Client is injectable."""

    def __init__(self, dataset_name: str, client=None):
        self.dataset_name = dataset_name
        if client is None:
            from langsmith import Client
            client = Client()
        self._client = client
        self._dataset = self._get_or_create_dataset()

    def _get_or_create_dataset(self):
        try:
            return self._client.read_dataset(dataset_name=self.dataset_name)
        except Exception:
            return self._client.create_dataset(
                dataset_name=self.dataset_name,
                description=f"Evaluation dataset for {self.dataset_name}",
            )

    def add_example(self, inputs: dict, outputs: dict, metadata: Optional[dict] = None) -> None:
        self._client.create_example(
            inputs=inputs,
            outputs=outputs,
            dataset_id=self._dataset.id,
            metadata=metadata or {},
        )

    def add_from_production_trace(self, run_id: str, reference_output: str) -> None:
        """Promote a good production run to a ground truth example."""
        run = self._client.read_run(run_id)
        self.add_example(
            inputs=run.inputs,
            outputs={"answer": reference_output},
            metadata={"promoted_from_run": run_id},
        )

    def size(self) -> int:
        return len(list(self._client.list_examples(dataset_id=self._dataset.id)))
