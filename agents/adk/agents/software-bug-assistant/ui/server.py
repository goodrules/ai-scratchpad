"""FastAPI backend for the Software Bug Assistant custom UI.

Uses get_fast_api_app() from google.adk.cli.fast_api to expose ADK endpoints
including /run_sse for SSE streaming, session CRUD, and /list-apps.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

# agents_dir is the project root (parent of software_bug_assistant/ package)
AGENTS_DIR = str(Path(__file__).parent.parent)

app: FastAPI = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=False,
    allow_origins=["http://localhost:3000"],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
