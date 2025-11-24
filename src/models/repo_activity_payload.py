from pydantic import BaseModel


class RepoActivityRequest(BaseModel):
    """
    Request body for summarizing recent activity for a repo.

    - repo_slug: "owner/repo"
    - branch: optional, defaults to "main"
    - max_* fields: how much to pull in each category
    """
    repo_slug: str          # e.g. "kknudson15/Agentic_AI"
    branch: str = "main"
    max_commits: int = 10
    max_prs: int = 5
    max_issues: int = 5