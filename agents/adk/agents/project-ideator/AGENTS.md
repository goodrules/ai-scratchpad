# Agent Guidelines: Project Ideator

## Verification Commands

- **Build / Install**: `uv sync --dev`
- **Test**: `PYTHONPATH=. uv run --with pytest --with pytest-asyncio python -m pytest tests/`
- **Lint**: `uv run --with ruff ruff check project_ideator`
- **Format Check**: `uv run --with ruff ruff format --check project_ideator`
- **Typecheck**: `uv run --with pyright pyright project_ideator`

## Architecture Invariants

- **A2UI Protocol & Event Interception**: Tools return structured A2UI envelopes; the A2A interceptor attaches `application/json+a2ui` DataParts exclusively to the conversational text artifact, never to tool execution artifacts.
- **Single-Surface Deduplication**: Each turn enforces unique, deduplicated surfaces (`beginRendering` + `surfaceUpdate` at most once per `surfaceId`) to prevent duplicate rendering in host clients like Gemini Enterprise.
- **5-Stage Sequential Pipeline**: Interview state flows monotonically (`problem_and_goal` -> `target_audience` -> `pain_and_alternatives` -> `scope_and_non_goals` -> `prd_draft`) accumulating validated requirements into `PRD.md`.
- **A2A JSON-RPC Contract**: Deployed service exposes compliant A2A endpoints (`/a2a/project_ideator`) and Vertex AI Agent Runtime adapters via Application Default Credentials without hardcoded IDs.

## Guardrails

### NEVER
- Commit `.env`, deployment metadata, secrets, project IDs/numbers, or runtime session databases.
- Manually edit `uv.lock` or modify lockfiles directly.
- Emit raw `<a2ui-json>` markup in model conversational text or tool response bodies.
- Alter the configured `MODEL_ID` or change model providers unless explicitly asked.

### ASK FIRST
- Adding, upgrading, or removing package dependencies in `pyproject.toml`.
- Altering A2UI schema definitions, catalog types, or tool argument/return signatures.
- Changing deployment scaffolding, Terraform scripts, or Cloud Run parameters.

### ALWAYS
- Execute all Python commands exclusively through `uv` (`uv run ...`).
- Run the full verification suite (tests, lint, typecheck) before declaring work complete.
- Follow surgical modification principles—touch only what is necessary, preserving existing code style and docstrings.
