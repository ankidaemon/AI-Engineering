"""
The intelligence vector store, scoped to one customer.

Every customer's briefs live in one pgvector table with a `customer_id` column,
the same way the rest of an application's data lives in shared tables. What makes
that safe is not the column, it is where the filter is enforced.

`IntelligenceVectorStore` has no search method. The only way to reach the data is
`for_customer(...)`, which returns a handle that stamps the id on every write and
puts it in the WHERE clause of every read. There is no call site that can forget
the filter, because there is no unscoped call to make. That is the property to
copy; a separate collection per customer is one way to get it, and a bad one once
you have more than a handful of customers.

pgvector filters in SQL, before the nearest neighbour search returns. A flat
FAISS index cannot: it takes a global top `fetch_k` and drops the rows that do
not match afterwards, so one large customer's documents can fill every slot and a
small customer's search comes back empty. Not a leak, but silently wrong
retrieval, and the reason a shared index needs a real database behind it.
"""
import logging

logger = logging.getLogger(__name__)


class InMemoryBackend:
    """
    A backend for local runs and tests. Keeps documents in a list and applies the
    metadata filter exactly, which is what pgvector does in SQL. Similarity is
    substring overlap, so it needs no embedding model and no network.
    """

    def __init__(self):
        self._docs: list = []

    def add(self, documents: list) -> int:
        self._docs.extend(documents)
        return len(documents)

    def search(self, query: str, k: int, where: dict) -> list:
        terms = {t for t in query.lower().split() if len(t) > 2}
        matches = [
            d for d in self._docs
            if all(d.metadata.get(key) == value for key, value in where.items())
        ]
        matches.sort(
            key=lambda d: sum(t in d.page_content.lower() for t in terms),
            reverse=True,
        )
        return matches[:k]

    def count(self) -> int:
        return len(self._docs)


def sqlalchemy_url(connection_url: str) -> str:
    """
    langchain-postgres goes through SQLAlchemy, which reads the scheme to pick a
    driver and defaults to psycopg2. We install psycopg 3, so a plain
    `postgresql://` URL fails at startup with a psycopg2 import error. The rest
    of the app talks to psycopg directly and wants the URL unchanged, so one
    setting serves both and this is the only place that knows the difference.
    """
    if connection_url.startswith("postgresql://"):
        return connection_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if connection_url.startswith("postgres://"):
        return connection_url.replace("postgres://", "postgresql+psycopg://", 1)
    return connection_url


class PgVectorBackend:
    """The real one. Requires langchain-postgres and a database with the
    `vector` extension installed (the docker-compose service ships with it)."""

    def __init__(self, connection_url: str, collection: str = "intelligence",
                 embeddings=None):
        from langchain_postgres import PGVector

        if embeddings is None:
            from langchain_ollama import OllamaEmbeddings
            from src.config import settings
            embeddings = OllamaEmbeddings(model=settings.embedding_model)

        self._store = PGVector(
            embeddings=embeddings,
            collection_name=collection,
            connection=sqlalchemy_url(connection_url),
            use_jsonb=True,
        )

    def add(self, documents: list) -> int:
        self._store.add_documents(documents)
        return len(documents)

    def search(self, query: str, k: int, where: dict) -> list:
        # langchain-postgres turns this into a JSONB predicate in the query, so
        # the filter runs in the database and the k rows that come back are
        # already this customer's k nearest.
        filter_dict = {key: {"$eq": value} for key, value in where.items()}
        return self._store.similarity_search(query, k=k, filter=filter_dict)

    def count(self) -> int:
        raise NotImplementedError("count the rows in SQL; not needed per request")


class CustomerScope:
    """A handle onto one customer's slice. The graph only ever holds one of these."""

    def __init__(self, backend, customer_id: str):
        self._backend = backend
        self._customer_id = customer_id

    @property
    def customer_id(self) -> str:
        return self._customer_id

    def add_documents(self, documents: list) -> int:
        if not documents:
            return 0
        for doc in documents:
            # stamped from the scope, never read from the document, so a caller
            # cannot write into another customer's slice by setting metadata
            doc.metadata["customer_id"] = self._customer_id
        return self._backend.add(documents)

    def similarity_search(self, query: str, k: int = 4, filter_dict=None) -> list:
        where = dict(filter_dict or {})
        where["customer_id"] = self._customer_id      # applied last, so it wins
        return self._backend.search(query, k, where)


class IntelligenceVectorStore:
    """Deliberately not searchable. Hand it to nothing that serves a request."""

    def __init__(self, backend):
        self._backend = backend

    def for_customer(self, customer_id) -> CustomerScope:
        if not customer_id or not str(customer_id).strip():
            raise ValueError("customer_id is required; refusing an unscoped store")
        return CustomerScope(self._backend, str(customer_id))

    def total_vector_count(self) -> int:
        """Across all customers. An operational number, never a customer's."""
        return self._backend.count()


def make_vector_store(kind: str = "memory", postgres_url: str = "",
                      collection: str = "intelligence", embeddings=None):
    if kind == "memory":
        return IntelligenceVectorStore(InMemoryBackend())
    if kind == "pgvector":
        return IntelligenceVectorStore(
            PgVectorBackend(postgres_url, collection, embeddings)
        )
    raise ValueError(f"unknown vector store kind: {kind!r}")
