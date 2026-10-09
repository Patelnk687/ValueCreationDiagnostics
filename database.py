"""Postgres access. UI never opens a connection itself."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from data import DEMO_CLIENTS, QUESTIONS
from scoring import POINTS, calculate_deal_score, risk_band, score_band

SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
PBKDF2_ROUNDS = 260_000


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip() or os.environ.get("DATABASE_URI", "").strip()
    if not url:
        try:
            import streamlit as st
            url = str(st.secrets.get("DATABASE_URL", "") or st.secrets.get("DATABASE_URI", "")).strip()
        except Exception:
            url = ""
    if not url:
        raise RuntimeError("DATABASE_URL is not set. See .streamlit/secrets.toml.example.")
    return url


def _secret(key: str, default: str = "") -> str:
    value = os.environ.get(key, "").strip()
    if value:
        return value
    try:
        import streamlit as st
        return str(st.secrets.get(key, default)).strip()
    except Exception:
        return default


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(calc.hex(), digest_hex)
    except Exception:
        return False


@contextmanager
def connect():
    conn = psycopg.connect(_database_url(), row_factory=dict_row, connect_timeout=10)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


ADMIN_KEY = "ValueCreation2026"


def init_db() -> None:
    with connect() as conn:
        for statement in SCHEMA.split(";"):
            sql = statement.strip()
            if sql:
                conn.execute(sql)
        firm = conn.execute("SELECT id FROM firms ORDER BY id LIMIT 1").fetchone()
        if not firm:
            firm = conn.execute(
                "INSERT INTO firms (name) VALUES (%s) RETURNING id",
                (_secret("FIRM_NAME", "Vetted Advisory"),),
            ).fetchone()
        question_count = conn.execute("SELECT COUNT(*) AS n FROM questions").fetchone()["n"]
        option_ids = _seed_questions(conn) if question_count == 0 else {}
        if _secret("SEED_DEMO", "0") == "1" and option_ids:
            _seed_demo_clients(conn, firm["id"], option_ids)
        email = _secret("ADVISOR_EMAIL")
        password = _secret("ADVISOR_PASSWORD")
        advisor_count = conn.execute("SELECT COUNT(*) AS n FROM advisor_users").fetchone()["n"]
        if advisor_count == 0 and "@" in email and len(password) >= 8:
            conn.execute(
                """
                INSERT INTO advisor_users (firm_id, username, display_name, email, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    firm["id"],
                    _secret("ADVISOR_USERNAME", "advisor"),
                    _secret("ADVISOR_NAME", "Advisor"),
                    email,
                    hash_password(password),
                ),
            )


def create_advisor_account(
    *,
    username: str,
    display_name: str,
    email: str,
    password: str,
    admin_key: str,
) -> dict:
    if admin_key != ADMIN_KEY:
        raise ValueError("Admin key is wrong.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Enter a valid email.")
    username = username.strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if not display_name.strip():
        raise ValueError("Name is required.")
    with connect() as conn:
        taken = conn.execute(
            """
            SELECT 1 FROM advisor_users
            WHERE lower(username) = lower(%s) OR lower(email) = lower(%s)
            """,
            (username, email.strip()),
        ).fetchone()
        if taken:
            raise ValueError("That username or email is already registered.")
        firm = conn.execute("SELECT id FROM firms ORDER BY id LIMIT 1").fetchone()
        if not firm:
            raise RuntimeError("No firm exists yet. Start the app once so the database can seed.")
        row = conn.execute(
            """
            INSERT INTO advisor_users (firm_id, username, display_name, email, password_hash)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, firm_id, display_name, email
            """,
            (firm["id"], username, display_name.strip(), email.strip(), hash_password(password)),
        ).fetchone()
    return _public_user(row, "advisor")


def _seed_questions(conn) -> dict:
    option_ids = {}
    for order, question in enumerate(QUESTIONS, start=1):
        qid = conn.execute(
            "INSERT INTO questions (field_key, prompt, display_order) VALUES (%s, %s, %s) RETURNING id",
            (question["field_key"], question["prompt"], order),
        ).fetchone()["id"]
        for rating, label in question["options"].items():
            oid = conn.execute(
                """
                INSERT INTO answer_options (question_id, rating, label, points)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                (qid, rating, label, POINTS[rating]),
            ).fetchone()["id"]
            option_ids[(question["field_key"], rating)] = oid
    return option_ids


def _seed_demo_clients(conn, firm_id: int, option_ids: dict) -> None:
    for demo in DEMO_CLIENTS:
        client_id = conn.execute(
            """
            INSERT INTO clients (firm_id, business_name, industry, annual_revenue, annual_ebitda, employee_count)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (
                firm_id,
                demo["business_name"],
                demo["industry"],
                demo["annual_revenue"],
                demo["annual_ebitda"],
                demo["employee_count"],
            ),
        ).fetchone()["id"]
        for key, rating in demo["answers"].items():
            qid = conn.execute("SELECT id FROM questions WHERE field_key = %s", (key,)).fetchone()["id"]
            conn.execute(
                """
                INSERT INTO questionnaire_responses (client_id, question_id, option_id)
                VALUES (%s, %s, %s)
                """,
                (client_id, qid, option_ids[(key, rating)]),
            )


def _public_user(row: dict, role: str) -> dict:
    return {
        "id": row["id"],
        "role": role,
        "display_name": row["display_name"],
        "email": row["email"],
        "firm_id": row.get("firm_id"),
        "client_id": row.get("client_id"),
    }


def login_advisor(username_or_email: str, password: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, firm_id, username, display_name, email, password_hash
            FROM advisor_users
            WHERE lower(username) = lower(%s) OR lower(email) = lower(%s)
            """,
            (username_or_email.strip(), username_or_email.strip()),
        ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return _public_user(row, "advisor")


def login_business(email: str, password: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, client_id, display_name, email, password_hash
            FROM business_users WHERE lower(email) = lower(%s)
            """,
            (email.strip(),),
        ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return _public_user(row, "business")


def create_business_account(
    *,
    business_name: str,
    industry: str,
    annual_revenue: int,
    annual_ebitda: int,
    employee_count: int,
    display_name: str,
    email: str,
    password: str,
) -> dict:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Enter a valid email.")
    if annual_revenue < 0 or employee_count < 0:
        raise ValueError("Revenue and employee count must be zero or greater.")
    with connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM business_users WHERE lower(email) = lower(%s)", (email.strip(),)
        ).fetchone()
        if exists:
            raise ValueError("An account with that email already exists.")
        firm = conn.execute("SELECT id FROM firms ORDER BY id LIMIT 1").fetchone()
        if not firm:
            raise RuntimeError("No advisor firm is seeded.")
        client_id = conn.execute(
            """
            INSERT INTO clients (firm_id, business_name, industry, annual_revenue, annual_ebitda, employee_count)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (firm["id"], business_name.strip(), industry.strip(), annual_revenue, annual_ebitda, employee_count),
        ).fetchone()["id"]
        row = conn.execute(
            """
            INSERT INTO business_users (client_id, display_name, email, password_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING id, client_id, display_name, email
            """,
            (client_id, display_name.strip(), email.strip(), hash_password(password)),
        ).fetchone()
    return _public_user(row, "business")


def list_questions() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT q.field_key, q.prompt, q.display_order, o.rating, o.label
            FROM questions q
            JOIN answer_options o ON o.question_id = q.id
            ORDER BY q.display_order, CASE o.rating WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END
            """
        ).fetchall()
    grouped = []
    by_key = {}
    for row in rows:
        item = by_key.get(row["field_key"])
        if not item:
            item = {
                "field_key": row["field_key"],
                "prompt": row["prompt"],
                "display_order": row["display_order"],
                "options": [],
            }
            by_key[row["field_key"]] = item
            grouped.append(item)
        item["options"].append({"rating": row["rating"], "label": row["label"]})
    return grouped


def submit_questionnaire(client_id: int, answers: dict) -> int:
    score = calculate_deal_score(answers)
    with connect() as conn:
        existing = conn.execute(
            "SELECT COUNT(*) AS n FROM questionnaire_responses WHERE client_id = %s",
            (client_id,),
        ).fetchone()["n"]
        if existing:
            raise ValueError("This assessment was already submitted.")
        for key, rating in answers.items():
            option = conn.execute(
                """
                SELECT o.id, q.id AS question_id
                FROM questions q
                JOIN answer_options o ON o.question_id = q.id
                WHERE q.field_key = %s AND o.rating = %s
                """,
                (key, rating),
            ).fetchone()
            if not option:
                raise ValueError(f"Unknown answer for {key}.")
            conn.execute(
                """
                INSERT INTO questionnaire_responses (client_id, question_id, option_id)
                VALUES (%s, %s, %s)
                """,
                (client_id, option["question_id"], option["id"]),
            )
    return score


def _decorate(client: dict, answers: list[dict], decisions: list[dict], include_private: bool) -> dict:
    ratings = {row["field_key"]: row["rating"] for row in answers}
    client["answers"] = answers
    client["submitted"] = len(ratings) == 10
    client["score"] = calculate_deal_score(ratings) if client["submitted"] else None
    if client["score"] is not None:
        client["readiness"] = score_band(client["score"])
        client["risk"] = risk_band(client["score"])
    else:
        client["readiness"] = None
        client["risk"] = None
    revenue = client["annual_revenue"] or 0
    ebitda = client["annual_ebitda"]
    client["ebitda_margin"] = (ebitda / revenue * 100) if revenue and ebitda is not None else None
    visible = []
    for decision in decisions:
        item = dict(decision)
        if not include_private:
            item.pop("private_note", None)
        visible.append(item)
    client["decisions"] = visible
    client["latest_decision"] = visible[0] if visible else None
    client["stage"] = _stage(client)
    return client


def _stage(client: dict) -> str:
    if not client["submitted"]:
        return "Profile only"
    latest = client["latest_decision"]
    if not latest:
        return "Awaiting review"
    if latest["decision"] == "clarification" and not latest.get("reply_message"):
        return "Clarification requested"
    if latest["decision"] == "clarification" and latest.get("reply_message"):
        return "Clarification received"
    if latest["decision"] == "accepted":
        return "Accepted"
    return "Rejected"


_CLIENT_SQL = """
SELECT c.id, c.firm_id, c.business_name, c.industry, c.annual_revenue,
       c.annual_ebitda, c.employee_count, c.created_at
FROM clients c
"""


def _load(conn, where_sql: str, params: tuple, include_private: bool) -> list[dict]:
    clients = conn.execute(_CLIENT_SQL + where_sql, params).fetchall()
    out = []
    for client in clients:
        answers = conn.execute(
            """
            SELECT q.field_key, q.prompt, q.display_order, o.rating, o.label, o.points
            FROM questionnaire_responses r
            JOIN questions q ON q.id = r.question_id
            JOIN answer_options o ON o.id = r.option_id
            WHERE r.client_id = %s
            ORDER BY q.display_order
            """,
            (client["id"],),
        ).fetchall()
        decisions = conn.execute(
            """
            SELECT d.id, d.decision, d.private_note, d.owner_message, d.created_at,
                   a.display_name AS advisor_name,
                   cr.message AS reply_message, cr.created_at AS reply_at
            FROM advisor_decisions d
            JOIN advisor_users a ON a.id = d.advisor_id
            LEFT JOIN clarification_replies cr ON cr.decision_id = d.id
            WHERE d.client_id = %s
            ORDER BY d.created_at DESC
            """,
            (client["id"],),
        ).fetchall()
        out.append(_decorate(dict(client), list(answers), list(decisions), include_private))
    return out


def list_clients(firm_id: int) -> list[dict]:
    with connect() as conn:
        return _load(conn, "WHERE c.firm_id = %s ORDER BY c.created_at DESC", (firm_id,), True)


def get_client_for_advisor(firm_id: int, client_id: int) -> dict | None:
    with connect() as conn:
        rows = _load(conn, "WHERE c.firm_id = %s AND c.id = %s", (firm_id, client_id), True)
    return rows[0] if rows else None


def get_owner_client(business_user_id: int) -> dict | None:
    with connect() as conn:
        link = conn.execute(
            "SELECT client_id FROM business_users WHERE id = %s", (business_user_id,)
        ).fetchone()
        if not link:
            return None
        rows = _load(conn, "WHERE c.id = %s", (link["client_id"],), False)
    return rows[0] if rows else None


def record_decision(
    *,
    firm_id: int,
    advisor_id: int,
    client_id: int,
    decision: str,
    owner_message: str,
    private_note: str,
) -> None:
    if decision not in {"accepted", "rejected", "clarification"}:
        raise ValueError("Unknown decision.")
    owner_message = owner_message.strip()
    private_note = private_note.strip()
    if len(owner_message) > 1000 or len(private_note) > 1000:
        raise ValueError("Messages are limited to 1,000 characters.")
    if decision == "clarification" and not owner_message:
        raise ValueError("Clarification requires a message the owner can read.")
    with connect() as conn:
        member = conn.execute(
            "SELECT 1 FROM advisor_users WHERE id = %s AND firm_id = %s",
            (advisor_id, firm_id),
        ).fetchone()
        client = conn.execute(
            "SELECT 1 FROM clients WHERE id = %s AND firm_id = %s",
            (client_id, firm_id),
        ).fetchone()
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM questionnaire_responses WHERE client_id = %s",
            (client_id,),
        ).fetchone()["n"]
        if not member or not client:
            raise PermissionError("That client is not in your firm.")
        if count != 10:
            raise ValueError("The owner has not submitted all ten answers.")
        conn.execute(
            """
            INSERT INTO advisor_decisions (client_id, advisor_id, decision, private_note, owner_message)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (client_id, advisor_id, decision, private_note, owner_message),
        )


def reply_to_clarification(*, business_user_id: int, message: str) -> None:
    message = message.strip()
    if not message or len(message) > 2000:
        raise ValueError("Reply must be 1 to 2,000 characters.")
    with connect() as conn:
        client = conn.execute(
            "SELECT client_id FROM business_users WHERE id = %s", (business_user_id,)
        ).fetchone()
        if not client:
            raise PermissionError("Unknown owner.")
        latest = conn.execute(
            """
            SELECT id, decision FROM advisor_decisions
            WHERE client_id = %s ORDER BY created_at DESC LIMIT 1
            """,
            (client["client_id"],),
        ).fetchone()
        if not latest or latest["decision"] != "clarification":
            raise ValueError("There is no open clarification request.")
        already = conn.execute(
            "SELECT 1 FROM clarification_replies WHERE decision_id = %s", (latest["id"],)
        ).fetchone()
        if already:
            raise ValueError("You already replied to this request.")
        conn.execute(
            """
            INSERT INTO clarification_replies (decision_id, business_user_id, message)
            VALUES (%s, %s, %s)
            """,
            (latest["id"], business_user_id, message),
        )
