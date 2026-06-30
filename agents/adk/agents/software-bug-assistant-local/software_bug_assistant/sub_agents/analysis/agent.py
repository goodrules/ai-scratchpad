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
from google.adk.code_executors import BuiltInCodeExecutor

from ...config import ANALYSIS_AGENT_DESCRIPTION, ANALYSIS_AGENT_MODEL, ANALYSIS_AGENT_NAME
from .prompt import ANALYSIS_INSTRUCTION

analysis_agent = Agent(
    name=ANALYSIS_AGENT_NAME,
    model=ANALYSIS_AGENT_MODEL,
    description=ANALYSIS_AGENT_DESCRIPTION,
    instruction=ANALYSIS_INSTRUCTION,
    code_executor=BuiltInCodeExecutor(),
)
