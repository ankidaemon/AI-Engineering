"""Product discovery: fit by retrieval, facts by filter (§5.1–§5.5)."""
from datetime import date

from src.products.advisor import (Customer, NO_FIT_MESSAGE, ProductAdvisor,
                                  build_query, eligible_offers, filter_products)
from src.products.catalog import (DEFAULT_CATALOG, DEFAULT_OFFERS,
                                  build_product_index)
from tests.conftest import FakeModel


def _by_id(product_id):
    return next(p for p in DEFAULT_CATALOG if p.product_id == product_id)


# ── The structured filter (Failure 2) ────────────────────────────────

def test_filter_drops_products_already_owned():
    customer = Customer("c1", income=100000, holdings=["travel-card"])
    kept = filter_products([_by_id("travel-card"), _by_id("cashback-card")], customer)
    assert [p.product_id for p in kept] == ["cashback-card"]


def test_filter_drops_ineligible_income():
    customer = Customer("c1", income=20000)
    kept = filter_products([_by_id("travel-card"), _by_id("student-card")], customer)
    assert [p.product_id for p in kept] == ["student-card"]


def test_filter_drops_missing_prerequisite():
    rich_but_new = Customer("c1", income=200000, holdings=[])
    kept = filter_products([_by_id("premium-travel-card")], rich_but_new)
    assert kept == []
    upgrader = Customer("c2", income=200000, holdings=["travel-card"])
    kept = filter_products([_by_id("premium-travel-card")], upgrader)
    assert [p.product_id for p in kept] == ["premium-travel-card"]


# ── Offers: checked, not matched (§5.5) ──────────────────────────────

def test_offer_outside_validity_window_is_dropped():
    customer = Customer("c1", income=100000)
    assert eligible_offers(DEFAULT_OFFERS, customer, date(2026, 12, 25)) == []


def test_offer_rules_enforced_inside_window():
    today = date(2026, 7, 15)
    low_income = Customer("c1", income=10000)
    ids = [o.offer_id for o in eligible_offers(DEFAULT_OFFERS, low_income, today)]
    assert ids == []                       # travel bonus needs income, cashback needs holding

    cardholder = Customer("c2", income=10000, holdings=["cashback-card"])
    ids = [o.offer_id for o in eligible_offers(DEFAULT_OFFERS, cardholder, today)]
    assert ids == ["cashback-groceries-2026"]


# ── End to end: retrieve, filter, explain (§5.2, §5.4) ───────────────

def test_recommends_travel_card_to_a_traveller(embeddings):
    index = build_product_index(DEFAULT_CATALOG, embeddings)
    model = FakeModel(reply="It waives foreign transaction fees, which suits "
                            "frequent travel abroad.")
    advisor = ProductAdvisor(index, model=model)
    customer = Customer("c1", income=60000, holdings=["everyday-savings"],
                        profile_notes="travels abroad often for work")

    rec = advisor.recommend(
        "I want a credit card with travel rewards and miles for flights abroad",
        customer)

    assert rec.found
    assert rec.product.product_id == "travel-card"
    # the explanation prompt was grounded in the product's stated features
    assert "no foreign transaction fees" in model.prompts[0]
    assert "Do not invent" in model.prompts[0]


def test_recommendation_never_includes_an_owned_product(embeddings):
    index = build_product_index(DEFAULT_CATALOG, embeddings)
    advisor = ProductAdvisor(index, model=FakeModel())
    owner = Customer("c1", income=60000, holdings=["travel-card"],
                     profile_notes="travels abroad often")

    rec = advisor.recommend("travel rewards credit card with miles", owner)
    if rec.found:
        assert rec.product.product_id != "travel-card"
        assert all(a.product_id != "travel-card" for a in rec.alternatives)


def test_no_fit_falls_back_honestly(embeddings):
    index = build_product_index([_by_id("premium-travel-card")], embeddings)
    advisor = ProductAdvisor(index, model=FakeModel())
    newcomer = Customer("c1", income=15000)

    rec = advisor.recommend("premium travel card with lounge access", newcomer)
    assert not rec.found
    assert rec.explanation == NO_FIT_MESSAGE


def test_query_combines_need_and_profile():
    customer = Customer("c1", profile_notes="student, first bank account")
    query = build_query("a card to build credit", customer)
    assert "build credit" in query and "student" in query


def test_recalled_memories_join_the_query_and_the_explanation(embeddings):
    """§2.5, §8.8: a fact stated weeks ago narrows today's search without
    the customer repeating themselves."""
    query = build_query("which card should I get",
                        Customer("c1"), memories=["travels abroad monthly"])
    assert "travels abroad monthly" in query

    index = build_product_index(DEFAULT_CATALOG, embeddings)
    model = FakeModel(reply="It suits your monthly travel.")
    advisor = ProductAdvisor(index, model=model)
    customer = Customer("c1", income=60000, holdings=["everyday-savings"])

    rec = advisor.recommend("which credit card is right for me", customer,
                            memories=["travels abroad monthly for work",
                                      "dislikes foreign transaction fees"])
    assert rec.found
    assert rec.product.product_id == "travel-card"
    # the memories reached the explanation prompt as profile context
    assert "travels abroad monthly" in model.prompts[0]
