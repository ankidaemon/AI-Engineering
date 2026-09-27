"""
The product advisor: need + profile + holdings (§5.1–§5.5).

The recommendation combines three things. The need is what the customer said.
The profile narrows it (income, relationship). The holdings rule things out.
Retrieval finds products that FIT (soft matching on the query built from need
and profile); a structured filter then enforces the FACTS (drop what the
customer already owns and what they cannot get), because facts the system
already knows must be filters, not something a model is trusted to remember
(Failure 2). The explanation is grounded in the product's own stated
features, never invented benefits (§5.4).

Offers follow the same shape: retrieval finds candidates, a rules check
keeps only the ones usable right now (§5.5).
"""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Customer:
    customer_id: str
    income: int = 0
    holdings: list = field(default_factory=list)   # product_ids already owned
    profile_notes: str = ""                        # e.g. "travels often"


@dataclass
class Recommendation:
    product: object = None                         # a Product, or None
    explanation: str = ""
    alternatives: list = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.product is not None


NO_FIT_MESSAGE = ("I could not find a product that fits right now. "
                  "Would you like to talk it through with an advisor?")

EXPLAIN_PROMPT = """You are a banking assistant recommending a product. \
Explain briefly and honestly why this product suits the customer, using ONLY \
the listed features. Do not invent benefits, rates, or terms.

Customer need: {need}
Customer profile: {profile}
Product: {name}
Features: {features}

Explanation:"""


def build_query(need: str, customer: Customer, memories: list = ()) -> str:
    """The need supplies the words; the profile supplies the context that
    narrows them (§5.2). Recalled memories join the query the same way the
    profile does (§8.8): a fact stated weeks ago narrows today's search."""
    query = f"{need}. Customer profile: {customer.profile_notes}".strip()
    if memories:
        query += " Remembered about this customer: " + "; ".join(memories)
    return query


def filter_products(products: list, customer: Customer) -> list:
    """Enforce the facts after retrieval finds the fit (§5.3)."""
    kept = []
    for p in products:
        if p.product_id in customer.holdings:
            continue                                  # already owns it
        if p.min_income and customer.income < p.min_income:
            continue                                  # not eligible
        if p.requires_holding and p.requires_holding not in customer.holdings:
            continue                                  # missing prerequisite
        kept.append(p)
    return kept


def eligible_offers(offers: list, customer: Customer, today: date) -> list:
    """Hard conditions are checked, not matched (§5.5). An expired offer can
    never slip through just because it read as a good fit."""
    kept = []
    for o in offers:
        if not (o.valid_from <= today.isoformat() <= o.valid_to):
            continue
        if o.min_income and customer.income < o.min_income:
            continue
        if o.requires_holding and o.requires_holding not in customer.holdings:
            continue
        kept.append(o)
    return kept


class ProductAdvisor:
    def __init__(self, product_index, model=None, k: int = 6):
        self._index = product_index
        self._model = model
        self._k = k

    def recommend(self, need: str, customer: Customer,
                  memories: list = ()) -> Recommendation:
        query = build_query(need, customer, memories)
        candidates = [product for product, _score in self._index.top_k(query, self._k)]
        fits = filter_products(candidates, customer)
        if not fits:
            return Recommendation(explanation=NO_FIT_MESSAGE)
        top = fits[0]
        return Recommendation(
            product=top,
            explanation=self._explain(need, customer, top, memories),
            alternatives=fits[1:3],
        )

    def _explain(self, need: str, customer: Customer, product,
                 memories: list = ()) -> str:
        model = self._model or _default_model()
        profile = "; ".join(
            part for part in [customer.profile_notes, *memories] if part)
        prompt = EXPLAIN_PROMPT.format(
            need=need, profile=profile or "not stated",
            name=product.name, features="; ".join(product.features),
        )
        response = model.invoke(prompt)
        return getattr(response, "content", str(response)).strip()


def _default_model():
    from langchain_ollama import ChatOllama
    from src.config import settings
    return ChatOllama(model=settings.quality_model,
                      base_url=settings.ollama_base_url)
