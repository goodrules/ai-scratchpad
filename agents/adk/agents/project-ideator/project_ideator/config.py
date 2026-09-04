"""Configuration settings for Project Ideator Agent."""

import os

from dotenv import load_dotenv

load_dotenv()

# Model configuration
MODEL_ID: str = os.getenv("MODEL_ID", "gemini-3.8-flash")
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.4"))
MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "4096"))

# A2UI Specification Version & Catalog URL
A2UI_VERSION: str = "v0.8"
A2UI_CATALOG_ID: str = "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"
A2UI_MIME_TYPE: str = "application/json+a2ui"

# Surface IDs
MAIN_SURFACE_ID: str = "project_ideation_surface"
PRD_SURFACE_ID: str = "prd_export_surface"

# Default PRD export filename
DEFAULT_PRD_FILENAME: str = "PRD.md"
