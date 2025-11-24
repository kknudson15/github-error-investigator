from typing import Optional
from pydantic import BaseModel, HttpUrl


class DailyReportRequest(BaseModel):
    """
    Request body for generating a combined daily report for a repo/branch.

    - Always summarizes repo activity.
    - Optionally includes an error investigation if error info is provided.
    """
    repo_slug: str           # e.g. "kknudson15/Agentic_AI"
    branch: str = "main"

    # Optional error context (if you want the report to include an error investigation)
    error_message: Optional[str] = None
    workflow_name: Optional[str] = None
    github_run_id: Optional[int] = None
    file_path: Optional[str] = None
    ci_url: Optional[HttpUrl] = None
    max_runs_to_check: int = 3

    # Activity limits
    max_commits: int = 10
    max_prs: int = 5
    max_issues: int = 5