import streamlit as st

import database as db

st.set_page_config(
    page_title="Vetted",
    page_icon=":material/shield:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db.init_db()

home = st.Page("pages/home.py", title="Home", url_path="", default=True)
advisor = st.Page("pages/advisor.py", title="Advisor", url_path="advisor")
business = st.Page("pages/business.py", title="Business", url_path="business")

nav = st.navigation([home, advisor, business], position="hidden")
nav.run()
