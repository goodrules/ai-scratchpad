from google.adk.workflow import Workflow, START
from google.adk import Agent
from google.adk.tools import google_search

# Step 1: Researcher (Uses Tools)
researcher = Agent(
    name="researcher",
    model="gemini-3.5-flash",
    instruction="Find 3 recent breakthroughs in the user provided topic using Google Search.",
    tools=[google_search]
)

# Step 2: Writer (Pure Reasoning)
writer = Agent(
    name="writer",
    model="gemini-3.5-flash",
    instruction="Summarize the provided research into a generic blog post format."
)

# Orchestrator (root_agent required for CLI)
root_agent = Workflow(
    name="blog_pipeline",
    description="Researches and writes a blog post.",
    edges=[
        (START, researcher, writer),
    ]
)
