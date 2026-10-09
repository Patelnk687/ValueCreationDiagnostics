import streamlit as st

import database as db
import ui

st.set_page_config(
    page_title="Vetted",
    page_icon=":material/shield:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db.init_db()

home = st.Page(ui.render_home, title="Home", url_path="", default=True)
advisor = st.Page(ui.render_advisor, title="Advisor", url_path="advisor")
business = st.Page(ui.render_business, title="Business", url_path="business")
ui.bind(home, advisor, business)

st.navigation([home, advisor, business], position="hidden").run()
