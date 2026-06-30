# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Map Generator Agent - Part 6 of the Location Strategy Pipeline.

This agent creates an interactive Google Maps visualization plotting all
recommended locations with color-coded markers and metadata InfoWindows.
"""

from google.adk import Agent
from google.genai import types

from ...callbacks import (
    after_map_generator,
    before_map_generator,
)
from ...config import FAST_MODEL, RETRY_ATTEMPTS, RETRY_INITIAL_DELAY
from ...prompt_utils import make_instruction_provider
from ...tools import generate_interactive_map

MAP_GENERATOR_INSTRUCTION = """You are a map visualization specialist creating interactive location maps for site selection analysis.

Your task is to generate an interactive Google Maps visualization of all recommended locations from the strategic analysis.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Your Mission
Create an interactive map that plots all locations from the strategic report with color-coded markers and metadata.

## Steps

### Step 1: Call the Tool
Call the generate_interactive_map tool. The tool reads everything it needs directly from session state (the strategic_report), so no arguments are required.

### Step 2: Report Result
After the tool returns, report the result:
- If successful: confirm how many locations were geocoded and mapped
- If any locations were skipped: mention which ones failed to geocode
- If failed: report the error for troubleshooting

## Output
The generate_interactive_map tool will return a result dict containing:
- status: "success" or "error"
- geocoded_count: Number of locations successfully plotted
- skipped_locations: List of locations that failed to geocode
- error_message: Error details (if failed)
"""

map_generator_agent = Agent(
    name="MapGeneratorAgent",
    model=FAST_MODEL,
    description="Generates interactive Google Maps visualization of recommended locations",
    instruction=make_instruction_provider(MAP_GENERATOR_INSTRUCTION, MAP_GENERATOR_INSTRUCTION),
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    tools=[generate_interactive_map],
    output_key="map_generation_result",
    before_agent_callback=before_map_generator,
    after_agent_callback=after_map_generator,
)
