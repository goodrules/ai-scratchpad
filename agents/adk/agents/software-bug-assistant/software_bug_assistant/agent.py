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

from google.adk import Agent

from .config import DEFAULT_MODEL, ROOT_AGENT_DESCRIPTION, ROOT_AGENT_NAME
from .prompt import agent_instruction
from .sub_agents import analysis_agent
from .tools.tools import (
    get_current_date,
    langchain_tool,
    mcp_tools,
    search_tool,
    toolbox_tools,
)

# Build tools list, filtering out empty/None values
tools = [get_current_date, search_tool]
if langchain_tool is not None:
    tools.append(langchain_tool)
if toolbox_tools:  # Only add if not empty list
    tools.extend(toolbox_tools)
if mcp_tools is not None:  # Only add if not None
    tools.append(mcp_tools)

root_agent = Agent(
    model=DEFAULT_MODEL,
    name=ROOT_AGENT_NAME,
    description=ROOT_AGENT_DESCRIPTION,
    instruction=agent_instruction,
    tools=tools,
    sub_agents=[analysis_agent],
)
