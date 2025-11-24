import asyncio

from dotenv import load_dotenv

from models.error_payload import ErrorInvestigationRequest
from agent.investigator import investigate_error


async def main():
    load_dotenv()

    payload = ErrorInvestigationRequest(
        error_message="ModuleNotFoundError: No module named 'my_pipeline.config'",
        repo_slug="your-org/your-repo",
        branch="main",
        workflow_name="CI",
        max_runs_to_check=3,
    )

    result = await investigate_error(payload)
    print(result["analysis_markdown"])


if __name__ == "__main__":
    asyncio.run(main())