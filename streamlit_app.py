import os
import asyncio

import streamlit as st
import requests
from dotenv import load_dotenv

# Load env so we can default the API base URL if needed
load_dotenv()

API_BASE_URL = os.getenv("INVESTIGATOR_API_BASE_URL", "http://localhost:8000")


def call_api(path: str, payload: dict) -> dict:
    url = f"{API_BASE_URL.rstrip('/')}{path}"
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


# ---------- Streamlit UI ----------

st.set_page_config(page_title="GitHub Error Investigator Demo", layout="wide")

st.title("🔎 GitHub Error Investigator & Activity Dashboard")

st.markdown(
    """
This dashboard talks to your **FastAPI + OpenAI Agent SDK + GitHub MCP** backend.

Use it to:
- Investigate a specific error for a repo/branch.
- Summarize recent repo activity (commits, PRs, issues).
- Generate a combined **daily report**.
"""
)

with st.sidebar:
    st.header("Backend config")
    st.write("Backend base URL:")
    api_url_input = st.text_input("API Base URL", API_BASE_URL)
    if api_url_input:
        API_BASE_URL = api_url_input

    st.caption("Make sure your FastAPI server is running on this URL.")

st.divider()

tab_investigate, tab_activity, tab_daily = st.tabs(
    ["Error investigation", "Repo activity", "Daily report"]
)

# --- Tab 1: Error investigation ---
with tab_investigate:
    st.subheader("Error investigation")

    repo_slug = st.text_input("Repo slug (owner/repo)", "kknudson15/Agentic_AI", key="inv_repo")
    branch = st.text_input("Branch", "main", key="inv_branch")
    error_message = st.text_area(
        "Error message / stack trace",
        "ModuleNotFoundError: No module named 'my_pipeline.config'",
        height=150,
        key="inv_error",
    )
    workflow_name = st.text_input("Workflow name (optional)", "", key="inv_workflow")
    github_run_id = st.text_input("GitHub run ID (optional)", "", key="inv_runid")
    ci_url = st.text_input("CI URL (optional)", "", key="inv_ciurl")

    max_runs_to_check = st.slider("Max runs to check", 1, 10, 3, key="inv_max_runs")

    if st.button("Run investigation", type="primary", key="inv_button"):
        payload = {
            "error_message": error_message,
            "repo_slug": repo_slug,
            "branch": branch,
            "workflow_name": workflow_name or None,
            "github_run_id": int(github_run_id) if github_run_id.strip() else None,
            "ci_url": ci_url or None,
            "max_runs_to_check": max_runs_to_check,
        }

        with st.spinner("Investigating error..."):
            try:
                resp = call_api("/investigate", payload)
                st.markdown(resp.get("analysis_markdown", "_No analysis returned._"))
            except Exception as e:
                st.error(f"Request failed: {e}")

# --- Tab 2: Repo activity ---
with tab_activity:
    st.subheader("Recent repo activity")

    repo_slug_a = st.text_input("Repo slug (owner/repo)", "kknudson15/Agentic_AI", key="act_repo")
    branch_a = st.text_input("Branch", "main", key="act_branch")

    max_commits = st.slider("Max commits", 1, 50, 10, key="act_commits")
    max_prs = st.slider("Max PRs", 0, 20, 5, key="act_prs")
    max_issues = st.slider("Max issues", 0, 20, 5, key="act_issues")

    if st.button("Summarize activity", type="primary", key="act_button"):
        payload = {
            "repo_slug": repo_slug_a,
            "branch": branch_a,
            "max_commits": max_commits,
            "max_prs": max_prs,
            "max_issues": max_issues,
        }

        with st.spinner("Summarizing activity..."):
            try:
                resp = call_api("/activity", payload)
                st.markdown(resp.get("activity_markdown", "_No activity summary returned._"))
            except Exception as e:
                st.error(f"Request failed: {e}")

# --- Tab 3: Daily report ---
with tab_daily:
    st.subheader("Daily report")

    repo_slug_d = st.text_input("Repo slug (owner/repo)", "kknudson15/Agentic_AI", key="daily_repo")
    branch_d = st.text_input("Branch", "main", key="daily_branch")

    st.markdown("**Optional error context** (include to add an investigation section):")
    error_message_d = st.text_area(
        "Error message / stack trace (optional)",
        "",
        height=120,
        key="daily_error",
    )
    workflow_name_d = st.text_input("Workflow name (optional)", "", key="daily_workflow")
    github_run_id_d = st.text_input("GitHub run ID (optional)", "", key="daily_runid")
    ci_url_d = st.text_input("CI URL (optional)", "", key="daily_ciurl")
    max_runs_to_check_d = st.slider("Max runs to check", 1, 10, 3, key="daily_max_runs")

    st.markdown("**Activity limits**:")
    max_commits_d = st.slider("Max commits", 1, 50, 10, key="daily_commits")
    max_prs_d = st.slider("Max PRs", 0, 20, 5, key="daily_prs")
    max_issues_d = st.slider("Max issues", 0, 20, 5, key="daily_issues")

    if st.button("Generate daily report", type="primary", key="daily_button"):
        payload = {
            "repo_slug": repo_slug_d,
            "branch": branch_d,
            "error_message": error_message_d or None,
            "workflow_name": workflow_name_d or None,
            "github_run_id": int(github_run_id_d) if github_run_id_d.strip() else None,
            "ci_url": ci_url_d or None,
            "max_runs_to_check": max_runs_to_check_d,
            "max_commits": max_commits_d,
            "max_prs": max_prs_d,
            "max_issues": max_issues_d,
        }

        with st.spinner("Generating daily report..."):
            try:
                resp = call_api("/daily_report", payload)
                st.markdown(resp.get("report_markdown", "_No report returned._"))
            except Exception as e:
                st.error(f"Request failed: {e}")