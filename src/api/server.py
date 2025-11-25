# src/api/server.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from agents import set_default_openai_key

from ..models.error_payload import ErrorInvestigationRequest
from ..models.repo_activity_payload import RepoActivityRequest
from ..models.daily_report_payload import DailyReportRequest
from ..models.pr_risk_payload import PRRiskRequest
from ..agent.investigator import (
    investigate_error,
    summarize_repo_activity,
    generate_daily_report,
    analyze_pr_risk,
)
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is required. "
        "Set it in your environment or .env file before starting the server."
    )

set_default_openai_key(openai_api_key)
# -------------------------------------------

app = FastAPI(
    title="GitHub Error Investigator (MCP)",
    version="0.1.0",
)


@app.post("/investigate")
async def investigate_endpoint(payload: ErrorInvestigationRequest):
    result = await investigate_error(payload)
    return JSONResponse(content=result)

@app.post("/activity")
async def activity_endpoint(payload: RepoActivityRequest):
    """
    Summarize recent repo activity (commits, PRs, issues) for a given repo/branch.
    """
    result = await summarize_repo_activity(payload)
    return JSONResponse(content=result)

@app.post("/daily_report")
async def daily_report_endpoint(payload: DailyReportRequest):
    """
    Generate a combined daily report for a repo/branch:
    - Recent repo activity
    - Optional error investigation (if error_message provided)
    """
    result = await generate_daily_report(payload)
    return JSONResponse(content=result)

@app.post("/pr_risk")
async def pr_risk_endpoint(payload: PRRiskRequest):
    """
    Analyze the risk profile of a specific pull request.
    """
    result = await analyze_pr_risk(payload)
    return JSONResponse(content=result)