import os
from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# 1. Setup a safe workspace directory
allowed_dir = os.path.abspath("./workspace")
if not os.path.exists(allowed_dir):
    os.makedirs(allowed_dir)

# 2. Configure the MCP Toolset (Runs the server via npx)
fs_mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", allowed_dir],
        )
    )
)

# 3. Create the Agent
root_agent = Agent(
    name="fs_agent",
    model="gemini-3.5-flash",
    instruction="""
    You are a file system assistant.
    You can read/write files in the workspace.
    Always verify file content after writing.
    """,
    tools=[fs_mcp_toolset]
)
