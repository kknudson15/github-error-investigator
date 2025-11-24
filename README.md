# GitHub Error Investigator (Agentic AI + MCP)

This project wires up the **official GitHub MCP server** to an **OpenAI Agents SDK** agent that can:

- Inspect recent GitHub workflow runs and logs
- Look at recent commits touching relevant files
- Correlate CI errors with code changes
- Return a markdown analysis with likely root causes + suggested fixes

It connects to the **hosted** GitHub MCP server at:

- `https://api.githubcopilot.com/mcp/` (remote server hosted by GitHub)
  - As documented in the [`github/github-mcp-server` README](https://github.com/github/github-mcp-server) under *Remote GitHub MCP Server*.
- Authenticated via a **GitHub Personal Access Token (PAT)** passed in the `Authorization: Bearer <TOKEN>` header.

## 1. Prerequisites

- Python 3.9+
- GitHub PAT with read permissions to your repos and workflows:
  - Typically: `repo`, `workflow`, and `read:org` if accessing org repos.
- OpenAI API key (`OPENAI_API_KEY`)

## 2. Setup

```bash
git clone https://github.com/your-org/github-error-investigator.git
cd github-error-investigator

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and set:
# OPENAI_API_KEY=...
# GITHUB_MCP_PAT=...