from typing import Optional
from pydantic import BaseModel, HttpUrl


class ErrorInvestigationRequest(BaseModel):
    error_message: str
    repo_slug: str  # e.g. "org/repo"
    branch: str = "main"
    workflow_name: Optional[str] = None
    github_run_id: Optional[int] = None
    file_path: Optional[str] = None
    ci_url: Optional[HttpUrl] = None
    max_runs_to_check: int = 5