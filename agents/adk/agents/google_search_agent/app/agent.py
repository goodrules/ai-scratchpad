from google.adk import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="google_search_agent",
    model="gemini-3.7-flash",
    description="Agent to answer questions using Google Search.",
    instruction="Answer the question using the Google Search tool.",
    tools=[google_search],
)

from google.adk.apps import App

app = App(root_agent=root_agent, name="app")
