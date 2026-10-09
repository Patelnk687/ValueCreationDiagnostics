"""Question bank transcribed from the sellability workbook, plus demo clients."""

QUESTIONS = [
    {
        "field_key": "team_execution",
        "prompt": "Can the team run the business and make decisions without the owner?",
        "options": {
            "high": "Yes. Managers run day-to-day operations and make decisions without the owner.",
            "medium": "Partly. The owner is still needed for important decisions.",
            "low": "No. The business stalls when the owner is away.",
        },
    },
    {
        "field_key": "owner_sales_reliance",
        "prompt": "Do new sales depend on the owner?",
        "options": {
            "high": "A sales team generates new business without the owner.",
            "medium": "The owner still closes a meaningful share of new sales.",
            "low": "Almost all new sales depend on the owner.",
        },
    },
    {
        "field_key": "relationship_ownership",
        "prompt": "Who owns the customer relationships?",
        "options": {
            "high": "The team holds the relationships. Customers stay if the owner leaves.",
            "medium": "Shared. Some key customers expect the owner.",
            "low": "The owner personally holds the important relationships.",
        },
    },
    {
        "field_key": "financial_quality",
        "prompt": "How reliable are the financial statements?",
        "options": {
            "high": "CPA-reviewed or audited statements a buyer could rely on.",
            "medium": "Compiled or bookkeeper-prepared statements with some gaps.",
            "low": "Internal or informal records that would not support diligence.",
        },
    },
    {
        "field_key": "revenue_growth",
        "prompt": "What is the recent revenue trend?",
        "options": {
            "high": "Revenue has been growing.",
            "medium": "Revenue is roughly flat or variable.",
            "low": "Revenue has been declining.",
        },
    },
    {
        "field_key": "customer_concentration",
        "prompt": "What share of revenue comes from the top three customers?",
        "options": {
            "high": "Under 15%.",
            "medium": "15% to 30%.",
            "low": "Over 30%.",
        },
    },
    {
        "field_key": "key_person_risk",
        "prompt": "How many departures would materially hurt the business?",
        "options": {
            "high": "No single departure would materially hurt the business.",
            "medium": "Losing one or two specific people would hurt.",
            "low": "Losing the owner or one key person would materially hurt the business.",
        },
    },
    {
        "field_key": "legal_cleanliness",
        "prompt": "Are there liens, lawsuits, tax issues, ownership disputes, or handshake deals?",
        "options": {
            "high": "No material legal, tax, or ownership issues. Contracts are written.",
            "medium": "Some open items, but nothing that would stop a sale.",
            "low": "Known liens, disputes, tax issues, or important handshake deals.",
        },
    },
    {
        "field_key": "asset_ownership",
        "prompt": "Does the company own the IP, brand, licenses, and other assets it needs?",
        "options": {
            "high": "Critical assets are owned by the company.",
            "medium": "Mostly, with some assets still in the owner's name.",
            "low": "Important assets sit with the owner or a third party.",
        },
    },
    {
        "field_key": "process_transferability",
        "prompt": "Could documented processes transfer to a new owner?",
        "options": {
            "high": "Core processes are documented and could transfer.",
            "medium": "Some documentation exists, but a lot is still in people's heads.",
            "low": "Processes live with the owner and are not documented.",
        },
    },
]

# Illustrative only. Not seeded into a production Supabase unless SEED_DEMO=1.
DEMO_CLIENTS = [
    {
        "business_name": "Northstar Logistics",
        "industry": "Logistics",
        "annual_revenue": 12_400_000,
        "annual_ebitda": 1_860_000,
        "employee_count": 48,
        "answers": {k: "high" for k in (
            "team_execution", "owner_sales_reliance", "relationship_ownership",
            "financial_quality", "revenue_growth", "customer_concentration",
            "key_person_risk", "legal_cleanliness",
        )} | {"asset_ownership": "medium", "process_transferability": "medium"},
    },
    {
        "business_name": "Harborlight Manufacturing",
        "industry": "Manufacturing",
        "annual_revenue": 8_200_000,
        "annual_ebitda": 740_000,
        "employee_count": 62,
        "answers": {
            "team_execution": "medium",
            "owner_sales_reliance": "medium",
            "relationship_ownership": "medium",
            "financial_quality": "high",
            "revenue_growth": "medium",
            "customer_concentration": "medium",
            "key_person_risk": "medium",
            "legal_cleanliness": "high",
            "asset_ownership": "high",
            "process_transferability": "low",
        },
    },
    {
        "business_name": "Cedar Ridge Services",
        "industry": "Home services",
        "annual_revenue": 2_100_000,
        "annual_ebitda": 180_000,
        "employee_count": 14,
        "answers": {k: "low" for k in (
            "team_execution", "owner_sales_reliance", "relationship_ownership",
            "financial_quality", "revenue_growth", "customer_concentration",
            "key_person_risk",
        )} | {
            "legal_cleanliness": "medium",
            "asset_ownership": "low",
            "process_transferability": "low",
        },
    },
]
