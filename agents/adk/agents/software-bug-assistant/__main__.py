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

import os

import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from software_bug_assistant.agent import root_agent
from software_bug_assistant.agent_executor import create_agent_executor


@click.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Host to bind to.")
@click.option("--port", default=8080, show_default=True, help="Port to listen on.")
def main(host: str, port: int) -> None:
    """Run the Software Bug Assistant A2A server."""
    app_url = os.environ.get("APP_URL", f"http://localhost:{port}")

    agent_card = AgentCard(
        name=root_agent.name,
        description=root_agent.description or "",
        url=f"{app_url.rstrip('/')}/",
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="search_tickets",
                name="Search Tickets",
                description="Search and find bug tickets",
                tags=["tickets", "search"],
            ),
            AgentSkill(
                id="manage_tickets",
                name="Manage Tickets",
                description="Create, update, and triage bug tickets",
                tags=["tickets", "management"],
            ),
            AgentSkill(
                id="analyze_tickets",
                name="Analyze Tickets",
                description="Perform trend analysis and statistical summaries on ticket data",
                tags=["tickets", "analysis"],
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )

    task_store = InMemoryTaskStore()
    agent_executor = create_agent_executor(root_agent)
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store,
    )

    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    uvicorn.run(app.build(), host=host, port=port)


if __name__ == "__main__":
    main()
