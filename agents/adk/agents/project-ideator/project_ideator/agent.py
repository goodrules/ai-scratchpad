"""Root agent definition for Project Ideator Agent."""

from __future__ import annotations

from google.adk import Agent
from google.genai import types

try:
    from .config import MAX_OUTPUT_TOKENS, MODEL_ID, TEMPERATURE
    from .prompt import SYSTEM_INSTRUCTION
    from .tools import (
        export_prd,
        get_ideation_stages,
        render_ideation_stage,
        render_prd_preview,
    )
except ImportError:
    from config import MAX_OUTPUT_TOKENS, MODEL_ID, TEMPERATURE
    from prompt import SYSTEM_INSTRUCTION
    from tools import (
        export_prd,
        get_ideation_stages,
        render_ideation_stage,
        render_prd_preview,
    )


root_agent = Agent(
    name="project_ideator",
    model=MODEL_ID,
    description="Interactive project ideation agent that grills software ideas using A2UI surfaces and produces a downloadable PRD.md.",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        get_ideation_stages,
        render_ideation_stage,
        render_prd_preview,
        export_prd,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    ),
)

from google.adk.apps import App

app = App(root_agent=root_agent, name="project_ideator")
