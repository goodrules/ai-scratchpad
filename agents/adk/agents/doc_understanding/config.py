import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Model ID for document understanding
MODEL_ID = os.environ.get("MODEL_ID", "gemini-3.7-flash")

# You can specify other model IDs or configurations here.
# For example:
# EMBEDDING_MODEL_ID = "text-embedding-004"
