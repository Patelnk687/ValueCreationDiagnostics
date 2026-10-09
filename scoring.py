"""Readiness index. Equal weight, 10/5/0. Not a valuation or close probability."""

REQUIRED_KEYS = (
    "team_execution",
    "owner_sales_reliance",
    "relationship_ownership",
    "financial_quality",
    "revenue_growth",
    "customer_concentration",
    "key_person_risk",
    "legal_cleanliness",
    "asset_ownership",
    "process_transferability",
)

POINTS = {"high": 10, "medium": 5, "low": 0}
RATINGS = frozenset(POINTS)


def calculate_deal_score(answers: dict) -> int:
    keys = set(answers)
    if keys != set(REQUIRED_KEYS):
        missing = set(REQUIRED_KEYS) - keys
        extra = keys - set(REQUIRED_KEYS)
        raise ValueError(f"answers must be exactly the ten keys; missing={sorted(missing)} extra={sorted(extra)}")
    total = 0
    for key in REQUIRED_KEYS:
        rating = answers[key]
        if rating not in RATINGS:
            raise ValueError(f"unknown rating for {key}: {rating!r}")
        total += POINTS[rating]
    return total


def score_band(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def risk_band(score: int) -> str:
    return {"High": "Low", "Medium": "Medium", "Low": "High"}[score_band(score)]
