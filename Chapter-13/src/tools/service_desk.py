"""
The bank's service system, behind an interface (§6.3).

In production this would be a client for the bank's real service platform.
Here it is a small in-memory implementation with the same surface, which is
exactly what makes the write tools testable offline: the tools depend on the
interface (`create`, `status`), not on a network.

Every created record returns a reference the customer can hold on to — the
ticket number of a complaint, the tracking id of a cheque book order. The
reference ties the conversation to the action, so a later "what happened to
my complaint" has a real handle to look up.
"""
import itertools


class ServiceDesk:
    _PREFIXES = {
        "complaint": "CMP",
        "callback": "CB",
        "cheque_book": "CHQ",
        "card_block": "BLK",
    }

    def __init__(self):
        self._records: dict = {}
        self._counter = itertools.count(1)

    def create(self, kind: str, fields: dict) -> str:
        prefix = self._PREFIXES.get(kind, "SR")
        reference = f"{prefix}-{next(self._counter):06d}"
        self._records[reference] = {"kind": kind, "status": "open", **fields}
        return reference

    def status(self, reference: str) -> dict:
        record = self._records.get(reference)
        if record is None:
            return {"reference": reference, "status": "not_found"}
        return {"reference": reference, **record}

    @property
    def record_count(self) -> int:
        return len(self._records)
