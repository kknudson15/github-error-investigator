from textwrap import dedent
from typing import Dict, Any

from agents import Agent, Runner
from agents.model_settings import ModelSettings
from agents.exceptions import MaxTurnsExceeded

from .github_mcp import github_mcp_server
from ..models.error_payload import ErrorInvestigationRequest
from ..models.repo_activity_payload import RepoActivityRequest
from ..models.daily_report_payload import DailyReportRequest
from ..models.pr_risk_payload import PRRiskRequest


def build_instructions() -> str:
    return dedent(
        """
        You are a senior DevOps + data engineering assistant.

        Your job:
        - Use the GitHub MCP tools to investigate build / pipeline errors.
        - You receive: an error message, GitHub repo slug, branch, optional run id, and optional file path.
        - You must:
          1. Inspect recent workflow runs and logs related to this error.
          2. Look at recent commits touching relevant files/components.
          3. Correlate the error message with code or config changes.
          4. Produce a concise root cause hypothesis + recommended fix.
          5. Additionally, provide a brief review of recent repo activity
             (recent commits, open pull requests, and recent issues) and
             highlight anything that might be related to the error.

        When using tools:
        - Prefer read-only operations (list workflow runs, view logs, list commits, diff commits, read files, list PRs/issues).
        - Avoid write actions (creating issues, comments, etc.) unless explicitly requested,
          which we are NOT doing in this project.

        Output:
        - Short summary (2–3 sentences).
        - Bullet list:
          - Likely cause(s)
          - Evidence (link / file / commit references)
          - Recommended fix steps
        - A separate section that summarizes recent repo activity.

        Keep explanations concrete and tied to specific commits, files, workflows,
        and pull requests whenever possible.
        """
    ).strip()

def build_activity_instructions() -> str:
    return dedent(
        """
        You are a senior DevOps + repository insights assistant.

        Your job:
        - Use the GitHub MCP tools to summarize recent activity for a given repo and branch.
        - You should:
          1. Look at the most recent commits on the branch.
          2. Look at recent open pull requests targeting this branch.
          3. Look at recent issues that may be associated with this repo.
          4. Highlight themes and anything that looks risky or noteworthy
             (e.g., big refactors, dependency changes, failing builds).
          5. Identify the **top 3 risky pull requests** and explain why they are risky.

        When using tools:
        - Prefer read-only operations (list commits, list PRs, list issues, read files).
        - Avoid write actions (creating issues, comments, etc.).

        How to judge PR risk:
        - Large number of changed files or lines.
        - Touches critical or core directories (e.g., services, pipelines, infra).
        - Modifies dependencies (requirements, package files, Dockerfiles).
        - Modifies CI/CD or workflow definitions.
        - Mentions breaking changes, migrations, or refactors in the title/description.
        - Associated with recent failing builds or issues.

        Output:
        - A concise but informative summary in Markdown:
          - Recent commit activity (what's being worked on, by whom).
          - Recent PR activity (major changes, refactors, dependency bumps).
          - Recent issues (bugs, performance problems, tech debt).
          - **A dedicated section listing the top 3 risky PRs and why they are risky.**

        Keep it high signal and concrete, with references to commit SHAs and PR numbers.
        """
    ).strip()

def build_pr_risk_instructions() -> str:
    return dedent(
        """
        You are a senior reviewer and production-readiness advisor.

        Your job:
        - Use the GitHub MCP tools to deeply analyze the risk profile of a given pull request.
        - You should:
          1. Fetch the pull request details (title, description, author, labels, status).
          2. Inspect the diff: files changed, lines added/removed, key directories touched.
          3. Look at related workflow runs for this PR (if available).
          4. Look for linked issues, references, or related PRs.
          5. Evaluate how risky this PR is to merge and why.

        How to judge risk:
        - Size and complexity of the diff.
        - Criticality of the areas touched (core services, infra, pipelines, security).
        - Changes to dependencies, environment, workflows, or configuration.
        - Presence of migrations, refactors, or breaking changes.
        - Test coverage (new tests added? existing tests modified?).
        - History of failures in related areas.

        Output:
        - A Markdown report with:
          - Overall risk rating (e.g., Low / Medium / High).
          - Clear reasons for the rating.
          - Specific files / components of concern.
          - Suggested checks before merge (tests, reviewers, rollout plan).

        Keep it concise but concrete and actionable.
        """
    ).strip()


def create_pr_risk_agent(server) -> Agent:
    """
    Agent specialized in analyzing the risk of a single PR.
    """
    return Agent(
        name="github-pr-risk-analyzer",
        instructions=build_pr_risk_instructions(),
        model="gpt-4.1-mini",
        mcp_servers=[server],
        model_settings=ModelSettings(
            tool_choice="auto",
            temperature=0.25,
        ),
    )


def create_repo_activity_agent(server) -> Agent:
    """
    Agent specialized in summarizing recent repo activity.
    """
    return Agent(
        name="github-repo-activity-summary",
        instructions=build_activity_instructions(),
        model="gpt-4.1-mini",   # adjust model if you want something heavier/lighter
        mcp_servers=[server],
        model_settings=ModelSettings(
            tool_choice="auto",
            temperature=0.3,
        ),
    )


def create_error_investigator_agent(server) -> Agent:
    """
    Given a connected MCP server, create an Agent wired to GitHub tools.
    """
    return Agent(
        name="github-error-investigator",
        instructions=build_instructions(),
        # You can change this to any supported model, e.g. "gpt-4.1" for deeper analysis
        model="gpt-4.1-mini",
        mcp_servers=[server],
        model_settings=ModelSettings(
            tool_choice="auto",
            temperature=0.2,
        ),
    )


async def investigate_error(payload: ErrorInvestigationRequest) -> Dict[str, Any]:
    """
    High-level orchestration:

    - Spins up MCP connection to GitHub
    - Runs the agent with a rich prompt composed from payload
    - Returns a dict ready to JSONify from FastAPI

    Includes defensive handling around MaxTurnsExceeded so the API
    returns a friendly message instead of a 500.
    """
    repo = payload.repo_slug
    branch = payload.branch

    user_prompt = dedent(
        f"""
        We have a CI / pipeline error to investigate.

        Error message:
        \"\"\"{payload.error_message}\"\"\"

        Repository: {repo}
        Branch: {branch}

        Additional context:
        - GitHub Run ID (if provided): {payload.github_run_id or "None"}
        - Workflow name (if provided): {payload.workflow_name or "None"}
        - Suspected file path (if provided): {payload.file_path or "None"}
        - CI URL (if provided): {payload.ci_url or "None"}
        - Max runs to check: {payload.max_runs_to_check}

        Using the GitHub MCP tools, you should:

        1. Investigate the error
           - Look up recent workflow runs / jobs that failed with a similar error.
           - Pull log excerpts around the failure.
           - Look at recent commits on this branch.
           - Focus on commits that touch the suspected file or related directories.
           - Infer the most likely root cause and propose concrete fixes.

        2. Review recent repo activity
           - List recent commits on this branch (e.g., last 5–10).
           - List recent open pull requests relevant to this branch.
           - List recent issues that may be related to this component or error.
           - Call out anything that looks related to the error (e.g., touching the
             same files, mentioning similar stack traces, changing dependencies).

        Return your answer in Markdown as:

        ## Summary
        - 2–3 sentences summarizing probable cause and impact.

        ## Likely causes
        - Bullet list of likely root causes with short explanations.

        ## Evidence
        - Bullet list of specific commits, PRs, workflow runs, log lines, or files
          you used to reach the conclusion.

        ## Recommended fixes
        - Bullet list of concrete actions: code changes, config updates, test additions,
          rollbacks, etc.

        ## Recent repo activity (last few commits / PRs / issues)
        - Short bullets summarizing recent activity on this repo/branch.
        - Highlight which items seem most related to the error and why.

        Include specific commit SHAs, filenames, workflow names, and PR numbers where relevant.
        """
    ).strip()

    async with github_mcp_server() as server:
        agent = create_error_investigator_agent(server)

        try:
            # Give the agent a bit more room than the default to use tools and reason.
            result = await Runner.run(
                agent,
                user_prompt,
                max_turns=20,
            )
            return {
                "analysis_markdown": result.final_output,
            }

        except MaxTurnsExceeded:
            # Return a friendly explanation instead of letting FastAPI raise 500
            fallback = dedent(
                f"""
                I attempted to investigate the error for:

                - Repository: `{repo}`
                - Branch: `{branch}`
                - Error: `{payload.error_message}`

                but I hit my internal step limit (too many back-and-forth steps between
                the model and the GitHub MCP tools).

                This usually means the GitHub MCP server isn't responding as expected
                (e.g., auth, connectivity, or protocol issues), so I kept retrying
                and eventually stopped.

                Please double-check:

                - That the GitHub MCP server is reachable and correctly configured.
                - That `GITHUB_MCP_PAT` has the right scopes for this repo.
                - That the repo slug and branch are correct.

                Once those are confirmed, try the request again.
                """
            ).strip()

            return {
                "analysis_markdown": fallback,
            }

async def summarize_repo_activity(payload: RepoActivityRequest) -> Dict[str, Any]:
    """
    Summarize recent activity (commits, PRs, issues) for a given repo/branch.

    Returns:
    - { "activity_markdown": "<markdown summary>" }
    """
    repo = payload.repo_slug
    branch = payload.branch

    user_prompt = dedent(
        f"""
        Summarize recent activity for this repository and branch.

        Repository: {repo}
        Branch: {branch}

        Activity limits:
        - Max commits: {payload.max_commits}
        - Max pull requests: {payload.max_prs}
        - Max issues: {payload.max_issues}

        Using the GitHub MCP tools, you should:
        - List the most recent commits on this branch (up to max_commits).
        - List recent open pull requests targeting this branch (up to max_prs).
        - List recent issues for this repo (up to max_issues).
        - Identify any themes (e.g., refactors, dependency updates, feature work).
        - Call out anything that looks risky or important (e.g., big changes,
          changes to critical paths, build pipeline modifications).
        - Identify the **top 3 risky pull requests**, based on factors like:
          - Size of the diff (files/lines changed).
          - Touching critical code paths or infrastructure.
          - Dependency / workflow / config changes.
          - Mentions of breaking changes, migrations, or refactors.
          - Association with failing builds or issues.

        Return your answer in Markdown as:

        ## Recent commit activity
        - ...

        ## Recent pull request activity
        - ...

        ## Recent issues
        - ...

        ## Top 3 risky PRs
        - For each PR, include:
          - PR number and title
          - Why it is considered risky
          - Key files/areas touched

        ## Notable risks / hotspots
        - Summarize any cross-cutting risks you see (e.g., multiple PRs touching
          the same fragile area, a lot of concurrent refactors, etc.).

        Include specific commit SHAs, PR numbers, and issue numbers where relevant.
        """
    ).strip()

    async with github_mcp_server() as server:
        agent = create_repo_activity_agent(server)

        try:
            result = await Runner.run(
                agent,
                user_prompt,
                max_turns=20,
            )
            return {
                "activity_markdown": result.final_output,
            }
        except MaxTurnsExceeded:
            fallback = dedent(
                f"""
                I attempted to summarize recent activity for:

                - Repository: `{repo}`
                - Branch: `{branch}`

                but I hit my internal step limit (too many back-and-forth steps
                between the model and the GitHub MCP tools).

                This usually means the GitHub MCP server isn't responding as expected
                (e.g., auth, connectivity, or protocol issues).

                Please verify:

                - The GitHub MCP server / remote endpoint is reachable.
                - `GITHUB_MCP_PAT` has the right scopes for this repo.
                - The repo slug and branch are correct.

                Once those are confirmed, try again.
                """
            ).strip()

            return {
                "activity_markdown": fallback,
            }

async def generate_daily_report(payload: DailyReportRequest) -> Dict[str, Any]:
    """
    Generate a combined daily report for a repo/branch:

    - Always includes recent repo activity (commits, PRs, issues).
    - Optionally includes an error investigation if error_message is provided.

    Returns:
    - { "report_markdown": "<markdown report>" }
    """
    repo = payload.repo_slug
    branch = payload.branch

    # 1) Always summarize repo activity
    activity_request = RepoActivityRequest(
        repo_slug=repo,
        branch=branch,
        max_commits=payload.max_commits,
        max_prs=payload.max_prs,
        max_issues=payload.max_issues,
    )
    activity_result = await summarize_repo_activity(activity_request)
    activity_md = activity_result.get("activity_markdown", "")

    # 2) Optionally run error investigation
    investigation_md = ""
    if payload.error_message:
        error_req = ErrorInvestigationRequest(
            error_message=payload.error_message,
            repo_slug=repo,
            branch=branch,
            workflow_name=payload.workflow_name,
            github_run_id=payload.github_run_id,
            file_path=payload.file_path,
            ci_url=payload.ci_url,
            max_runs_to_check=payload.max_runs_to_check,
        )
        investigation_result = await investigate_error(error_req)
        investigation_md = investigation_result.get("analysis_markdown", "")

    # 3) Combine into a single Markdown report
    header = dedent(
        f"""
        # Daily Report for `{repo}` ({branch})

        Generated by the GitHub Error Investigator + Activity Summary agent.
        """
    ).strip()

    if payload.error_message:
        error_section = dedent(
            f"""
            ## Error investigation

            _Error message:_

            ```text
            {payload.error_message}
            ```

            {investigation_md or "No investigation details available."}
            """
        ).strip()
    else:
        error_section = dedent(
            """
            ## Error investigation

            No specific error was provided for this report.
            """
        ).strip()

    activity_section = dedent(
        f"""
        ## Recent repo activity

        {activity_md or "No activity details available."}
        """
    ).strip()

    report_markdown = "\n\n".join([header, error_section, activity_section])

    return {"report_markdown": report_markdown}

async def analyze_pr_risk(payload: PRRiskRequest) -> Dict[str, Any]:
    """
    Analyze the risk profile of a single pull request.

    Returns:
    - { "pr_risk_markdown": "<markdown analysis>" }
    """
    repo = payload.repo_slug
    pr_number = payload.pr_number

    user_prompt = dedent(
        f"""
        Analyze the risk of the following pull request.

        Repository: {repo}
        Pull request number: {pr_number}

        Using the GitHub MCP tools, you should:
        - Fetch PR metadata (title, description, author, labels, status).
        - Inspect the diff: which files changed, how many lines added/removed,
          which directories or subsystems are affected.
        - Identify changes to dependencies, configuration, workflows, or infra.
        - Check test-related files (unit/integration tests, CI config) to see
          if coverage was added or modified.
        - Look for workflow runs associated with this PR and whether they passed.
        - Consider any linked issues or referenced PRs.

        Return your answer in Markdown as:

        ## Summary
        - Overall risk rating: Low / Medium / High
        - One or two lines explaining the rating.

        ## Reasons for risk rating
        - Bullet list of concrete reasons (e.g., core service touched,
          large refactor, migration, dependency bump).

        ## Key files / areas touched
        - Bullet list of important files/directories and what changed.

        ## Tests & workflows
        - What tests or workflows cover this PR?
        - Are there gaps or missing coverage?

        ## Recommendations before merge
        - Concrete steps: additional tests, reviewers, rollout strategy,
          feature flags, canary deployment, etc.

        Include the PR number and key file paths in your explanations.
        """
    ).strip()

    async with github_mcp_server() as server:
        agent = create_pr_risk_agent(server)

        try:
            result = await Runner.run(
                agent,
                user_prompt,
                max_turns=20,
            )
            return {
                "pr_risk_markdown": result.final_output,
            }
        except MaxTurnsExceeded:
            fallback = dedent(
                f"""
                I attempted to analyze the risk of:

                - Repository: `{repo}`
                - Pull request: `#{pr_number}`

                but I hit my internal step limit (too many back-and-forth steps
                between the model and the GitHub MCP tools).

                This usually means the GitHub MCP server isn't responding as expected
                (e.g., auth, connectivity, or protocol issues).

                Please verify:

                - The GitHub MCP server / remote endpoint is reachable.
                - `GITHUB_MCP_PAT` has the right scopes for this repo.
                - The repo slug and PR number are correct.

                Once those are confirmed, try again.
                """
            ).strip()

            return {
                "pr_risk_markdown": fallback,
            }