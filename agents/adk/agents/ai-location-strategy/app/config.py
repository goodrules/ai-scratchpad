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

"""Configuration for Retail AI Location Strategy ADK Agent.

This agent supports both Google AI Studio and Vertex AI authentication modes.

For LOCAL DEVELOPMENT (AI Studio):
    GOOGLE_API_KEY=your_google_api_key
    GOOGLE_GENAI_USE_VERTEXAI=FALSE
    MAPS_API_KEY=your_maps_api_key

For PRODUCTION DEPLOYMENT (Vertex AI):
    GOOGLE_CLOUD_PROJECT=your-project-id
    GOOGLE_CLOUD_LOCATION=us-central1
    GOOGLE_GENAI_USE_VERTEXAI=TRUE
    MAPS_API_KEY=your_maps_api_key
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
app_dir = Path(__file__).parent
project_root = app_dir.parent
# Try project root .env first, then app/.env as fallback
env_path = project_root / ".env"
if not env_path.exists():
    env_path = app_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Detect authentication mode from environment
USE_VERTEX_AI = (
    os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper() == "TRUE"
)

# Vertex AI Configuration (for production deployment)
if USE_VERTEX_AI:
    GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_CLOUD_LOCATION = os.environ.get(
        "GOOGLE_CLOUD_LOCATION", "global"
    )
    GOOGLE_API_KEY = ""  # Not used in Vertex AI mode
else:
    # AI Studio Configuration (for local development)
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
    GOOGLE_CLOUD_PROJECT = ""
    GOOGLE_CLOUD_LOCATION = "global"

# Maps API Key (required for both modes)
MAPS_API_KEY = os.environ.get("MAPS_API_KEY", "")
# Model Configuration
# ============================================================================
# Default models standardizing on gemini-3.7-flash
# ============================================================================

FAST_MODEL = "gemini-3.7-flash"
PRO_MODEL = "gemini-3.7-flash"
CODE_EXEC_MODEL = "gemini-3.7-flash"
IMAGE_MODEL = "gemini-3.1-flash-image"

# Retry Configuration (native HttpRetryOptions for 429 and transient errors)
RETRY_INITIAL_DELAY = 2  # seconds
RETRY_ATTEMPTS = 5       # total attempts
RETRY_MAX_DELAY = 60     # seconds cap


def get_retry_http_options():
    """Return standard HttpOptions configured with exponential backoff and jitter."""
    from google.genai import types

    return types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=RETRY_ATTEMPTS,
            initial_delay=float(RETRY_INITIAL_DELAY),
            max_delay=float(RETRY_MAX_DELAY),
            exp_base=2.0,
            jitter=1.0,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        )
    )


# App Configuration
APP_NAME = "ai_location_strategy"
