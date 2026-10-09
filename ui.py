"""Landing page, owner portal, advisor desk."""

from __future__ import annotations

import streamlit as st

import database as db
from scoring import POINTS

MONEY = lambda n: "Not provided" if n is None else f"${n / 1_000_000:.1f}M"
HOME = ADVISOR = BUSINESS = None


def bind(home, advisor, business) -> None:
    global HOME, ADVISOR, BUSINESS
    HOME, ADVISOR, BUSINESS = home, advisor, business


def inject() -> None:
    st.markdown(f"<style>{open('styles.css', encoding='utf-8').read()}</style>", unsafe_allow_html=True)


def header() -> None:
    if HOME is not None:
        st.page_link(HOME, label="VETTED", icon=":material/shield:")
    st.caption("Directional sale-readiness screen. Not a valuation or a close probability.")


def sign_out() -> None:
    for key in ("auth_user", "auth_role", "wizard", "selected_client"):
        st.session_state.pop(key, None)
    st.rerun()


def render_home() -> None:
    inject()
    header()
    st.title("See whether a business is ready to talk about a sale.")
    st.write(
        "Early sale talks start with revenue and a price. Buyers also need to know if the company "
        "runs without the founder, who owns the customers, whether the numbers are usable, and "
        "whether people, assets, and processes can transfer. Vetted turns that into one shared intake."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.page_link(BUSINESS, label="Business owner portal", icon=":material/storefront:")
        if st.button("Open owner portal", type="primary", use_container_width=True):
            st.switch_page(BUSINESS)
    with c2:
        st.page_link(ADVISOR, label="Advisor desk", icon=":material/work:")
        if st.button("Open advisor desk", use_container_width=True):
            st.switch_page(ADVISOR)

    st.subheader("Five stages")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.markdown("**1. Profile.** Name, industry, revenue, EBITDA, headcount.")
    s2.markdown("**2. Ten answers.** Team, sales, customers, financials, concentration, legal, assets, process.")
    s3.markdown("**3. Score.** 10 / 5 / 0. High, Medium, or Low readiness.")
    s4.markdown("**4. Advisor decision.** Accept, reject, or request clarification.")
    s5.markdown("**5. Owner reply.** One reply to a clarification. Status updates in the portal.")

    preview = st.tabs(["Owner", "Advisor", "Shared record"])
    with preview[0]:
        st.markdown("The owner signs up, answers ten questions once, and sees a readiness band. They do not see the numeric score or the advisor's private note.")
    with preview[1]:
        st.markdown("The advisor sees every client in the firm, the 0–100 score, the inverse risk band, each answer with its points, and decision history.")
    with preview[2]:
        st.markdown("Accept, reject, and clarification are stored. A clarification can take one owner reply. A newer decision replaces the current status. Earlier updates stay in history.")

    a, b, c = st.columns(3)
    a.markdown("**Owner.** Ten structured answers and a plain High / Medium / Low band.")
    b.markdown("**Advisor.** Same answers, a 0–100 score, an inverse risk band, and a recorded decision.")
    c.markdown("**Shared record.** Accept, reject, or ask for clarification. The owner replies in the portal.")

    st.subheader("How scoring works")
    st.markdown(
        "Each of 10 questions is **10** (strong), **5** (mixed), or **0** (needs attention). "
        "Score = 10×H + 5×M. **70–100 High readiness / Low risk. 40–69 Medium. 0–39 Low readiness / High risk.** "
        "Revenue, EBITDA, and headcount are profile only. They do not add points."
    )
    st.markdown(
        '<p class="v-muted">Illustrative: eight strong and two mixed answers = 90/100, High readiness, Low risk. '
        "Self-reported. Verify before any transaction advice.</p>",
        unsafe_allow_html=True,
    )


def render_business() -> None:
    inject()
    header()
    user = st.session_state.get("auth_user")
    if not user or st.session_state.get("auth_role") != "business":
        _business_auth()
        return
    st.write(f"Signed in as **{user['display_name']}**")
    if st.button("Sign out"):
        sign_out()
    client = db.get_owner_client(user["id"])
    if not client["submitted"]:
        _wizard(client)
    else:
        _owner_result(user, client)


def _business_auth() -> None:
    login, signup = st.tabs(["Sign in", "Create account"])
    with login:
        with st.form("biz_login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", type="primary"):
                user = db.login_business(email, password)
                if not user:
                    st.error("Email or password is wrong.")
                else:
                    st.session_state.auth_user = user
                    st.session_state.auth_role = "business"
                    st.rerun()
    with signup:
        with st.form("biz_signup"):
            business_name = st.text_input("Business name")
            industry = st.text_input("Industry")
            revenue = st.number_input("Annual revenue (USD)", min_value=0, step=1000, value=0)
            ebitda = st.number_input("Annual EBITDA (USD, can be negative)", step=1000, value=0)
            employees = st.number_input("Employees", min_value=0, step=1, value=0)
            name = st.text_input("Your name")
            email = st.text_input("Email", key="su_email")
            password = st.text_input("Password (8+ characters)", type="password", key="su_pw")
            if st.form_submit_button("Create account", type="primary"):
                if not business_name.strip() or not industry.strip() or not name.strip():
                    st.error("Business name, industry, and your name are required.")
                    st.stop()
                try:
                    user = db.create_business_account(
                        business_name=business_name,
                        industry=industry,
                        annual_revenue=int(revenue),
                        annual_ebitda=int(ebitda),
                        employee_count=int(employees),
                        display_name=name,
                        email=email,
                        password=password,
                    )
                except (ValueError, RuntimeError) as exc:
                    st.error(str(exc))
                else:
                    st.session_state.auth_user = user
                    st.session_state.auth_role = "business"
                    st.rerun()


def _wizard(client: dict) -> None:
    questions = db.list_questions()
    draft = st.session_state.setdefault("wizard", {})
    step = int(draft.get("step", 0))
    step = max(0, min(step, len(questions) - 1))
    st.progress((step + 1) / len(questions), text=f"Question {step + 1} of {len(questions)}")
    q = questions[step]
    st.subheader(q["prompt"])
    labels = {opt["label"]: opt["rating"] for opt in q["options"]}
    current = draft.get(q["field_key"])
    default_label = next((label for label, rating in labels.items() if rating == current), None)
    choice = st.radio(
        "Answer",
        list(labels),
        index=list(labels).index(default_label) if default_label else 0,
        label_visibility="collapsed",
    )
    draft[q["field_key"]] = labels[choice]
    left, right = st.columns(2)
    if step > 0 and left.button("Back"):
        draft["step"] = step - 1
        st.rerun()
    if step < len(questions) - 1:
        if right.button("Next", type="primary"):
            draft["step"] = step + 1
            st.rerun()
    elif right.button("Submit assessment", type="primary"):
        answers = {item["field_key"]: draft.get(item["field_key"]) for item in questions}
        try:
            db.submit_questionnaire(client["id"], answers)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state.pop("wizard", None)
            st.rerun()


def _owner_result(user: dict, client: dict) -> None:
    band = client["readiness"]
    color = {"High": "v-green", "Medium": "v-amber", "Low": "v-red"}[band]
    st.markdown(f'<p class="v-kicker">Readiness</p><h1 class="{color}">{band}</h1>', unsafe_allow_html=True)
    st.caption(f"{client['business_name']} · {client['industry']} · {MONEY(client['annual_revenue'])} revenue")
    latest = client["latest_decision"]
    if not latest:
        status = "Awaiting advisor review"
    elif latest["decision"] == "clarification" and latest.get("reply_message"):
        status = "Clarification sent"
    elif latest["decision"] == "clarification":
        status = "Clarification requested"
    elif latest["decision"] == "accepted":
        status = "Accepted"
    else:
        status = "Not moving forward"
    st.markdown(f"**Status.** {status}")
    if latest and latest.get("owner_message"):
        st.info(latest["owner_message"])
    if latest and latest["decision"] == "clarification" and not latest.get("reply_message"):
        with st.form("reply"):
            message = st.text_area("Reply to your advisor", max_chars=2000)
            if st.form_submit_button("Send reply", type="primary"):
                try:
                    db.reply_to_clarification(business_user_id=user["id"], message=message)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
    if st.button("Check for updates"):
        st.rerun()
    st.subheader("Updates")
    if not client["decisions"]:
        st.caption("No advisor update yet.")
    for item in client["decisions"]:
        st.markdown(f"**{item['decision']}** · {item['created_at']}")
        if item.get("owner_message"):
            st.write(item["owner_message"])
        if item.get("reply_message"):
            st.caption(f"Your reply: {item['reply_message']}")
    with st.expander("Your answers"):
        for row in client["answers"]:
            st.write(f"{row['display_order']}. {row['prompt']}")
            st.caption(row["label"])


def render_advisor() -> None:
    inject()
    header()
    user = st.session_state.get("auth_user")
    if not user or st.session_state.get("auth_role") != "advisor":
        login, signup = st.tabs(["Sign in", "Create advisor login"])
        with login:
            with st.form("adv_login"):
                username = st.text_input("Username or email")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Sign in", type="primary"):
                    found = db.login_advisor(username, password)
                    if not found:
                        st.error("Username or password is wrong.")
                    else:
                        st.session_state.auth_user = found
                        st.session_state.auth_role = "advisor"
                        st.rerun()
        with signup:
            with st.form("adv_signup"):
                name = st.text_input("Your name")
                username = st.text_input("Username")
                email = st.text_input("Email")
                password = st.text_input("Password (8+ characters)", type="password")
                admin_key = st.text_input("Admin key", type="password")
                if st.form_submit_button("Create advisor login", type="primary"):
                    try:
                        found = db.create_advisor_account(
                            username=username,
                            display_name=name,
                            email=email,
                            password=password,
                            admin_key=admin_key,
                        )
                    except (ValueError, RuntimeError) as exc:
                        st.error(str(exc))
                    else:
                        st.session_state.auth_user = found
                        st.session_state.auth_role = "advisor"
                        st.rerun()
        return
    st.write(f"**{user['display_name']}**")
    if st.button("Sign out"):
        sign_out()
    clients = db.list_clients(user["firm_id"])
    submitted = [c for c in clients if c["submitted"]]
    decided = [c for c in clients if c["latest_decision"]]
    avg = round(sum(c["score"] for c in submitted) / len(submitted)) if submitted else 0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Clients", len(clients))
    m2.metric("Submitted", len(submitted))
    m3.metric("Avg readiness", avg if submitted else "—")
    m4.metric("Decisions", len(decided))

    query = st.text_input("Search company or industry")
    stage = st.selectbox("Stage", ["All", "Profile only", "Awaiting review", "Clarification requested", "Clarification received", "Accepted", "Rejected"])
    sort = st.selectbox("Sort", ["Newest", "Score high", "Score low", "Name"])
    rows = clients
    if query:
        q = query.lower()
        rows = [c for c in rows if q in c["business_name"].lower() or q in c["industry"].lower()]
    if stage != "All":
        rows = [c for c in rows if c["stage"] == stage]
    if sort == "Name":
        rows = sorted(rows, key=lambda c: c["business_name"].lower())
    elif sort == "Score high":
        rows = sorted(rows, key=lambda c: c["score"] if c["score"] is not None else -1, reverse=True)
    elif sort == "Score low":
        rows = sorted(rows, key=lambda c: c["score"] if c["score"] is not None else 101)
    else:
        rows = sorted(rows, key=lambda c: c["created_at"], reverse=True)

    if not rows:
        st.caption("No clients match.")
        return
    labels = {f"{c['business_name']} · {c['stage']}": c["id"] for c in rows}
    selected_label = st.selectbox("Client", list(labels))
    client = db.get_client_for_advisor(user["firm_id"], labels[selected_label])
    _audit(user, client)


def _audit(user: dict, client: dict) -> None:
    st.subheader(client["business_name"])
    st.caption(f"{client['industry']} · {client['stage']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", MONEY(client["annual_revenue"]))
    c2.metric("EBITDA", MONEY(client["annual_ebitda"]))
    c3.metric("Employees", client["employee_count"] if client["employee_count"] is not None else "Not provided")
    margin = client["ebitda_margin"]
    c4.metric("EBITDA margin", "N/A" if margin is None else f"{margin:.1f}%")
    if client["score"] is None:
        st.warning("Questionnaire is not complete. No score and no decision yet.")
        return
    st.markdown(
        f'<p class="v-cyan">{client["score"]}/100</p><p>Readiness {client["readiness"]} · Risk {client["risk"]}</p>',
        unsafe_allow_html=True,
    )
    st.progress(client["score"] / 100)
    groups = {"Strong · 10": [], "Mixed · 5": [], "Needs attention · 0": []}
    for row in client["answers"]:
        bucket = {10: "Strong · 10", 5: "Mixed · 5", 0: "Needs attention · 0"}[POINTS[row["rating"]]]
        groups[bucket].append(row)
    tabs = st.tabs([f"{name} ({len(items)})" for name, items in groups.items()])
    for tab, items in zip(tabs, groups.values()):
        with tab:
            for row in items:
                st.markdown(f"**{row['prompt']}**")
                st.write(row["label"])
                st.caption(f"{POINTS[row['rating']]} points")
    with st.form("decision"):
        decision = st.selectbox("Decision", ["accepted", "rejected", "clarification"])
        owner_message = st.text_area("Message the owner sees (required for clarification)", max_chars=1000)
        private_note = st.text_area("Private note (advisor only)", max_chars=1000)
        if st.form_submit_button("Record decision", type="primary"):
            try:
                db.record_decision(
                    firm_id=user["firm_id"],
                    advisor_id=user["id"],
                    client_id=client["id"],
                    decision=decision,
                    owner_message=owner_message,
                    private_note=private_note,
                )
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))
            else:
                st.rerun()
    st.subheader("Decision history")
    for item in client["decisions"]:
        st.markdown(f"**{item['decision']}** · {item['advisor_name']} · {item['created_at']}")
        if item.get("owner_message"):
            st.write(f"Owner message: {item['owner_message']}")
        if item.get("private_note"):
            st.caption(f"Private: {item['private_note']}")
        if item.get("reply_message"):
            st.write(f"Owner reply: {item['reply_message']}")
