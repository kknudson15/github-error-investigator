from pydantic import BaseModel


class PRRiskRequest(BaseModel):
    """
    Request body for analyzing the risk of a specific pull request.

    - repo_slug: "owner/repo"
    - pr_number: GitHub pull request number
    """
    repo_slug: str        # e.g. "kknudson15/Agentic_AI"
    pr_number: int