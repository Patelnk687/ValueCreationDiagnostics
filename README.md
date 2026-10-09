# Vetted

Sale-readiness screen for a business owner and an advisor. Postgres on Supabase. UI on Streamlit.

Not a valuation, a diligence report, or a probability of closing.

## Secrets

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.

`DATABASE_URL` is the Supabase **transaction pooler** URI (port 6543). In the Supabase SQL editor, run nothing by hand; the app applies `schema.sql` on startup.

`ADVISOR_EMAIL` and `ADVISOR_PASSWORD` are read only when `firms` is empty. They seed one firm and one advisor. After that, changing the secrets does not reset the password.

Set `SEED_DEMO=1` only if you want the three fictional clients (Northstar, Harborlight, Cedar Ridge).

## Local

```bash
python -m venv .venv
source .venv/bin/activate   # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud

1. Push this repo to GitHub.
2. New app, main file `app.py`.
3. Paste the same secrets into App settings → Secrets.
4. Deploy. Data lives in Supabase, so a Cloud restart does not wipe accounts.

## Scoring

10 questions, 10 / 5 / 0 points. 70–100 High readiness (Low risk), 40–69 Medium, 0–39 Low readiness (High risk). Profile dollars are not in the score.
