"""
Turning a request into a customer.

Everything else in this chapter's isolation story depends on one thing: the
customer id is derived from a credential the server verifies, never read from
the request body. That is the whole point. If a caller can name their own
customer id, namespaces and ownership checks are decoration.

The verification here is a hashed API key lookup, which is the smallest thing
that is honestly a credential check. A real deployment swaps this function for
OIDC, a session cookie, or mTLS. Nothing downstream changes, because everything
downstream only ever sees the customer id this returns.
"""
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)


class Unauthenticated(Exception):
    """No credential, or one that does not verify."""


def parse_api_keys(raw: str) -> dict:
    """
    Read `key1:customer-a,key2:customer-b` into a lookup keyed by the SHA-256 of
    the key, so the process never holds the plaintext after startup.
    """
    keys = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        key, customer = pair.split(":", 1)
        key, customer = key.strip(), customer.strip()
        if key and customer:
            keys[hashlib.sha256(key.encode()).hexdigest()] = customer
    return keys


class ApiKeyAuthenticator:
    def __init__(self, raw_keys: str = ""):
        self._keys = parse_api_keys(raw_keys)
        if not self._keys:
            logger.warning("no API keys configured: every request will be rejected")

    def customer_for(self, api_key) -> str:
        """The authenticated customer id, or raise. Never returns a default."""
        if not api_key:
            raise Unauthenticated("missing API key")
        digest = hashlib.sha256(api_key.encode()).hexdigest()
        for known, customer in self._keys.items():
            # compare_digest so a wrong key takes the same time as a right one
            if hmac.compare_digest(known, digest):
                return customer
        raise Unauthenticated("unrecognised API key")
