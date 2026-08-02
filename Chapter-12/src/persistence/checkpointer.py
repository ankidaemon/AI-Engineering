"""
Checkpointer factory.

LangGraph saves the state of a run through a checkpointer, so a workflow can be
resumed after a crash and so many instances can share progress. For local runs a
SQLite file is enough. For a multi instance production deployment you want
Postgres, so every replica reads and writes the same store. The choice is driven
by config, and the heavy imports are lazy so a laptop never needs a database.
"""
import logging

logger = logging.getLogger(__name__)


def make_checkpointer(kind: str = "sqlite", sqlite_path: str = "./data/intel.db",
                      postgres_url: str = ""):
    """
    Return a checkpointer for the requested backend.

      "memory"   in process only, wiped on restart. Good for tests.
      "sqlite"   a local file, survives restarts on a single machine.
      "postgres" shared across instances, the production choice.
    """
    if kind == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()

    if kind == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver
        return SqliteSaver.from_conn_string(sqlite_path)

    if kind == "postgres":
        # Requires langgraph-checkpoint-postgres and a reachable database.
        from langgraph.checkpoint.postgres import PostgresSaver
        saver = PostgresSaver.from_conn_string(postgres_url)
        saver.setup()
        return saver

    raise ValueError(f"unknown checkpointer kind: {kind!r}")
