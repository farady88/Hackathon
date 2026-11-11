"""Lynceus UI. Start the API first, then from the repo root: streamlit run Streamlit_UI/app.py"""
import os

import requests
import streamlit as st

API = os.environ.get("LYNCEUS_API", "http://127.0.0.1:8000")


def call(method, path, **kwargs):
    """Call the API and show the result, or a readable error."""
    try:
        r = requests.request(method, API + path, timeout=60, **kwargs)
    except requests.ConnectionError:
        st.error(f"Cannot reach the API at {API}. Start it with: uvicorn Fast_API.main:app --reload")
        return None
    if r.status_code >= 400:
        st.error(f"{r.status_code}: {r.json().get('detail', r.text)}")
        return None
    return r.json()


st.title("Lynceus")

st.header("Ask a question")
with st.form("ask"):
    question = st.text_input("Question")
    if st.form_submit_button("Ask") and question.strip():
        result = call("POST", "/ask", json={"question": question})
        if result:
            st.write(result["answer"])

st.header("Look up a case")
with st.form("case"):
    case_id = st.text_input("Case ID", placeholder="case-142")
    if st.form_submit_button("Look up") and case_id.strip():
        result = call("GET", f"/records/{case_id.strip()}")
        if result:
            st.json(result)
