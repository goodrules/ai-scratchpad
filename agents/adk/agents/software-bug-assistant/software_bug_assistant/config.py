# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# --- Model IDs ---
DEFAULT_MODEL = "gemini-3.7-flash" # gemini-3.7-flash
ANALYSIS_AGENT_MODEL = DEFAULT_MODEL
SEARCH_AGENT_MODEL = DEFAULT_MODEL

# --- Agent metadata ---
ROOT_AGENT_NAME = "software_assistant"
ROOT_AGENT_DESCRIPTION = (
    "Triages and debugs software issues, manages bug tickets, "
    "and performs ticket analysis."
)

SEARCH_AGENT_NAME = "search_agent"

ANALYSIS_AGENT_NAME = "analysis_agent"
ANALYSIS_AGENT_DESCRIPTION = (
    "Analyzes bug ticket data using Python code execution. Delegate when the "
    "user requests trend analysis, pattern detection, statistical summaries, "
    "or any quantitative analysis of ticket data."
)

# --- Tool config ---
TOOLBOX_DEFAULT_URL = "http://127.0.0.1:5000"
TOOLBOX_TOOLSET_NAME = "tickets_toolset"


def resolve_toolbox_url() -> str:
    """Resolve MCP Toolbox URL: env var -> gcloud Cloud Run -> localhost default."""
    import os
    url = os.getenv("MCP_TOOLBOX_URL")
    if url:
        return url
    try:
        import subprocess
        result = subprocess.run(
            ["gcloud", "run", "services", "describe", "toolbox",
             "--format=value(status.url)", "--region=us-central1"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return TOOLBOX_DEFAULT_URL

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"
GITHUB_MCP_TOOL_FILTER = [
    "search_repositories",
    "search_issues",
    "list_issues",
    "get_issue",
    "list_pull_requests",
    "get_pull_request",
]

# --- Misc ---
DATE_FORMAT = "%Y-%m-%d"
COMPANY_NAME = "Airline Inc"
COMPANY_TYPE = "airline"
