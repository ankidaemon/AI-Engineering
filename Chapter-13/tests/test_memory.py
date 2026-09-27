"""The memory seam: namespaced per customer, injected client (§2, §8.8)."""
from src.memory.service import MemoryService
from src.workers.tasks import remember_exchange_impl


class FakeMem0:
    """Speaks the mem0 2.x surface the service uses: add(messages, user_id=),
    search(query, top_k=, filters={"user_id": ...}), delete_all(user_id=)."""

    def __init__(self):
        self.store = {}                      # user_id -> [memory text]
        self.added = []

    def add(self, messages, user_id=None):
        self.added.append((user_id, messages))
        text = " ".join(m["content"] for m in messages)
        self.store.setdefault(user_id, []).append(text)

    def search(self, query, top_k=3, filters=None):
        rows = self.store.get(filters["user_id"], [])[:top_k]
        return {"results": [{"memory": m} for m in rows]}

    def delete_all(self, user_id=None):
        self.store.pop(user_id, None)


def test_remember_hands_mem0_the_full_exchange():
    client = FakeMem0()
    MemoryService(client).remember("c1", "I travel monthly", "Noted!")
    (user_id, messages), = client.added
    assert user_id == "c1"
    assert [m["role"] for m in messages] == ["user", "assistant"]


def test_recall_returns_only_this_customers_facts():
    """Failure 7: the namespace is enforced inside the service, so one
    customer's memories can never inform another's answer."""
    client = FakeMem0()
    service = MemoryService(client)
    service.remember("c1", "I fly to Singapore twice a month", "Noted.")
    service.remember("c2", "I am a student with my first account", "Welcome!")

    recalled = service.recall("c2", "which card suits me")
    assert recalled and all("Singapore" not in fact for fact in recalled)
    assert service.recall("stranger", "which card suits me") == []


def test_the_raw_mem0_client_is_not_reachable_around_the_namespace():
    """The namespace rule is only worth something if there is no unscoped
    call to make. A public client would be exactly that call."""
    service = MemoryService(FakeMem0())
    assert not hasattr(service, "client")
    for name in ("remember", "recall", "forget"):
        assert "customer_id" in getattr(service, name).__code__.co_varnames


def test_recall_k_limits_what_the_request_path_carries():
    client = FakeMem0()
    service = MemoryService(client, recall_k=2)
    for i in range(5):
        service.remember("c1", f"fact number {i}", "ok")
    assert len(service.recall("c1", "anything")) == 2


def test_forget_erases_one_customer_and_leaves_the_rest():
    client = FakeMem0()
    service = MemoryService(client)
    service.remember("c1", "I moved to Pune", "Noted.")
    service.remember("c2", "I run a small business", "Noted.")
    service.forget("c1")
    assert service.recall("c1", "where do I live") == []
    assert service.recall("c2", "my business") != []


def test_background_task_is_a_thin_wrapper_over_the_service():
    """§7.3: extraction costs a model call, so remembering runs in a worker.
    The impl takes the service as an argument and is tested directly."""
    client = FakeMem0()
    result = remember_exchange_impl("c1", "I travel monthly", "Noted!",
                                    MemoryService(client))
    assert result == {"customer_id": "c1", "remembered": True}
    assert client.store["c1"]
