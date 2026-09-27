"""
The assistant: the router and the three specialists, wired together (§8).

One message flows: route it (one vector search — question, advice, or
action, no model call), hand it to the matching specialist, shape the reply.
On the question path the semantic cache is consulted first and only safe
answers are offered back to it — the cache itself enforces the boundary
(§7.4), so a customer-specific or handed-off answer can never be stored
even if this code forgets to check.

Memory joins at two points (§8.8). Before advice, the customer's own
memories are recalled (a vector search) and handed to the advisor. After
any reply, the finished exchange goes out through the `remember` seam —
in production a callable that enqueues a Celery task, so Mem0's extraction
never runs while the customer waits.

Every dependency is injected, which is what lets the whole flow run in a
test with fakes and no infrastructure.
"""
from dataclasses import dataclass, field


@dataclass
class Reply:
    kind: str                     # "question" | "advice" | "action"
    text: str
    reference: str = ""
    needs_confirmation: bool = False
    sources: list = field(default_factory=list)
    from_cache: bool = False


class Assistant:
    def __init__(self, knowledge_service, advisor, action_agent, router,
                 cache=None, get_customer=None, memory=None, remember=None):
        self._knowledge = knowledge_service
        self._advisor = advisor
        self._actions = action_agent
        self._router = router
        self._cache = cache
        self._get_customer = get_customer or (lambda cid: None)
        self._memory = memory
        self._remember = remember

    def handle(self, customer_id: str, message: str, history: list = (),
               confirmed: bool = False) -> Reply:
        kind = self._router.route(message)

        if kind == "question":
            reply = self._answer_question(message)
        elif kind == "advice":
            customer = self._get_customer(customer_id)
            memories = (self._memory.recall(customer_id, message)
                        if self._memory else [])
            rec = self._advisor.recommend(message, customer, memories=memories)
            reply = Reply(kind="advice", text=rec.explanation,
                          reference=rec.product.product_id if rec.found else "")
        else:
            result = self._actions.handle(message, list(history), customer_id,
                                          confirmed=confirmed)
            reply = Reply(kind="action", text=result.message,
                          reference=result.reference,
                          needs_confirmation=(result.status == "needs_confirmation"))

        self._store_memory(customer_id, message, reply)
        return reply

    def _store_memory(self, customer_id: str, message: str, reply: Reply):
        """The exchange leaves through the remember seam after the reply is
        composed. Two kinds are skipped, because Mem0 reads a long prompt
        for every exchange it is given and these tell it nothing about the
        customer (§8.16). A cache hit is a replay of an answer already given.
        An action turn is an instruction ("block my card", "yes, go ahead")
        and its reply is a status or a reference number."""
        if reply.from_cache or reply.kind == "action":
            return
        if self._remember is not None:
            self._remember(customer_id, message, reply.text)
        elif self._memory is not None:
            self._memory.remember(customer_id, message, reply.text)

    def _answer_question(self, message: str) -> Reply:
        if self._cache is not None:
            cached = self._cache.get(message)
            if cached is not None:
                return Reply(kind="question", text=cached, from_cache=True)
        answer = self._knowledge.ask(message)
        if self._cache is not None and not answer.handed_off:
            # General knowledge only; the cache double-checks the boundary.
            self._cache.put(message, answer.text, kind="knowledge")
        return Reply(kind="question", text=answer.text, sources=answer.sources)
