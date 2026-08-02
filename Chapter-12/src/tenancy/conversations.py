"""
Conversation ownership.

A LangGraph thread id is a database key: whoever presents it gets that thread's
checkpointed state. So the id has to be minted by the server, has to be
unguessable, and every reuse has to be checked against the caller. Taking an id
from the request body and prefixing it with a tenant name looks like a check but
is not one, because the client still chooses the rest of the string.

The check is an ownership lookup, and this module owns it. `resolve` is the only
way the API turns a request into a thread id.
"""
import uuid
import logging

logger = logging.getLogger(__name__)


class ConversationAccessDenied(Exception):
    """The caller asked for a conversation that is not theirs, or does not exist."""


class ConversationStore:
    """
    Base class holding the rules. Subclasses only supply storage.

    Conversations are per customer and long lived: a new id per request would
    defeat the checkpointer, which exists so a conversation continues and so a
    crashed run resumes where it stopped. New per conversation, checked on every
    reuse, is the property we want.
    """

    def _put(self, conversation_id: str, customer_id: str) -> None:
        raise NotImplementedError

    def owner_of(self, conversation_id: str):
        raise NotImplementedError

    def start(self, customer_id: str) -> str:
        if not customer_id or not customer_id.strip():
            raise ValueError("cannot start a conversation without a customer")
        conversation_id = str(uuid.uuid4())
        self._put(conversation_id, customer_id)
        return conversation_id

    def resolve(self, customer_id: str, conversation_id=None) -> str:
        """
        Turn an authenticated caller plus an optional conversation id into a
        thread id. No id means start a new conversation. An id that the caller
        does not own is refused.
        """
        if conversation_id is None:
            return self.start(customer_id)

        owner = self.owner_of(conversation_id)
        if owner is None or owner != customer_id:
            # One error for both cases on purpose. Distinguishing "no such
            # conversation" from "not yours" tells an attacker which ids exist.
            logger.warning("refused conversation %s for customer %s",
                           conversation_id, customer_id)
            raise ConversationAccessDenied("unknown or inaccessible conversation")
        return conversation_id


class InMemoryConversations(ConversationStore):
    """For local runs and tests. Ownership is lost on restart, like the memory
    checkpointer it pairs with."""

    def __init__(self):
        self._owners: dict = {}

    def _put(self, conversation_id: str, customer_id: str) -> None:
        self._owners[conversation_id] = customer_id

    def owner_of(self, conversation_id: str):
        return self._owners.get(conversation_id)


class PostgresConversations(ConversationStore):
    """
    The production store. Lives in the same database as the checkpoints and the
    vectors, so a customer's whole footprint is one transaction to delete.
    """

    def __init__(self, connection_url: str):
        import psycopg
        self._connect = lambda: psycopg.connect(connection_url)
        self._setup()

    def _setup(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id          UUID PRIMARY KEY,
                    customer_id TEXT        NOT NULL,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS conversations_customer_idx "
                "ON conversations (customer_id)"
            )

    def _put(self, conversation_id: str, customer_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations (id, customer_id) VALUES (%s, %s)",
                (conversation_id, customer_id),
            )

    def owner_of(self, conversation_id: str):
        try:
            uuid.UUID(conversation_id)
        except (ValueError, AttributeError, TypeError):
            return None            # not even a uuid, so it cannot be one of ours
        with self._connect() as conn:
            row = conn.execute(
                "SELECT customer_id FROM conversations WHERE id = %s",
                (conversation_id,),
            ).fetchone()
        return row[0] if row else None


def make_conversation_store(kind: str = "memory", postgres_url: str = ""):
    """`memory` for local runs and tests, `postgres` for anything real."""
    if kind == "memory":
        return InMemoryConversations()
    if kind == "postgres":
        return PostgresConversations(postgres_url)
    raise ValueError(f"unknown conversation store kind: {kind!r}")
