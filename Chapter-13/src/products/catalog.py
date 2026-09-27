"""
The product catalog, described for retrieval (§5.2).

Product discovery is a retrieval problem, not a rules engine: each product
carries a rich plain-language description written the way a colleague would
explain it, and retrieval finds the ones that match a customer's situation.
The structured attributes alongside the description are what the advisor
filters on afterwards — eligibility and holdings are facts to enforce, not
things to leave to a model's memory (§5.3, Failure 2).

Offers (§5.5) carry hard conditions — a validity window, eligibility rules —
that are checked, not matched.
"""
from dataclasses import dataclass, field


@dataclass
class Product:
    product_id: str
    name: str
    category: str                 # "card" | "account" | "loan"
    description: str              # rich retrieval text, in customers' language
    features: list = field(default_factory=list)   # the facts explanations cite
    min_income: int = 0           # eligibility floor, 0 = open to all
    requires_holding: str = ""    # product_id that must already be held, if any
    annual_fee: str = "none"

    @property
    def retrieval_text(self) -> str:
        return f"{self.name}. {self.description} " + " ".join(self.features)


@dataclass
class Offer:
    offer_id: str
    title: str
    description: str
    product_id: str               # the product the offer applies to
    valid_from: str               # ISO dates; checked, not matched (§5.5)
    valid_to: str
    min_income: int = 0
    requires_holding: str = ""


DEFAULT_CATALOG = [
    Product(
        product_id="everyday-savings",
        name="Everyday Savings Account",
        category="account",
        description=("A simple savings account for day-to-day banking, with no "
                     "minimum balance and no monthly charges. A good first "
                     "account for a new customer or a student."),
        features=["no minimum balance", "no monthly account fee",
                  "instant transfers to any bank"],
    ),
    Product(
        product_id="student-card",
        name="Student Credit Card",
        category="card",
        description=("A starter credit card for students and first-time "
                     "cardholders building a credit history, with a low limit "
                     "and no annual fee."),
        features=["no annual fee", "low starting credit limit",
                  "credit history reported monthly"],
    ),
    Product(
        product_id="cashback-card",
        name="Cashback Credit Card",
        category="card",
        description=("A credit card that returns a share of everyday spending "
                     "on groceries, fuel, and bills as cashback. Suits someone "
                     "who wants low fees and simple rewards on daily spending."),
        features=["2 percent cashback on groceries and fuel",
                  "45 day interest free period", "no annual fee in year one"],
        min_income=25000,
        annual_fee="waived in year one",
    ),
    Product(
        product_id="travel-card",
        name="Travel Rewards Credit Card",
        category="card",
        description=("A credit card for people who travel often. It earns "
                     "miles on every purchase and waives foreign transaction "
                     "fees, so spending abroad costs nothing extra."),
        features=["no foreign transaction fees", "2 miles per unit spent",
                  "airport lounge access twice a year",
                  "45 day interest free period"],
        min_income=40000,
        annual_fee="95",
    ),
    Product(
        product_id="premium-travel-card",
        name="Premium Travel Card",
        category="card",
        description=("The top-tier travel card for frequent flyers who already "
                     "bank with us. Unlimited lounge access, higher miles "
                     "earning, and comprehensive travel insurance."),
        features=["unlimited airport lounge access", "3 miles per unit spent",
                  "full travel insurance included",
                  "no foreign transaction fees"],
        min_income=80000,
        requires_holding="travel-card",
        annual_fee="450",
    ),
    Product(
        product_id="business-account",
        name="Small Business Account",
        category="account",
        description=("A current account for small business owners, with "
                     "invoicing tools, an overdraft line, and an accountant "
                     "access seat included."),
        features=["free invoicing tools", "overdraft up to an agreed limit",
                  "accountant access included"],
        min_income=30000,
    ),
]


DEFAULT_OFFERS = [
    Offer(
        offer_id="travel-bonus-2026",
        title="Travel card welcome miles",
        description=("20,000 bonus miles when you take the Travel Rewards "
                     "Credit Card and spend within the first three months."),
        product_id="travel-card",
        valid_from="2026-06-01", valid_to="2026-09-30",
        min_income=40000,
    ),
    Offer(
        offer_id="cashback-groceries-2026",
        title="Double cashback on groceries",
        description="4 percent cashback on groceries for existing cashback cardholders.",
        product_id="cashback-card",
        valid_from="2026-07-01", valid_to="2026-08-31",
        requires_holding="cashback-card",
    ),
]


def build_product_index(products: list, embeddings) -> "CosineIndex":
    """Embed every product's retrieval text once, at startup (§5.2)."""
    from src.vectorstores.cosine_index import CosineIndex
    index = CosineIndex(embeddings)
    index.add([(p.retrieval_text, p) for p in products])
    return index


def build_offer_index(offers: list, embeddings) -> "CosineIndex":
    from src.vectorstores.cosine_index import CosineIndex
    index = CosineIndex(embeddings)
    index.add([(f"{o.title}. {o.description}", o) for o in offers])
    return index
