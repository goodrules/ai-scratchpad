# Project Ideator Agent (ADK + A2UI)

An interactive project ideation agent built with the **Google Agent Development Kit (ADK)**, **Gemini 3.8 Flash**, and the **A2UI (Agent to UI)** declarative UI protocol.

The agent guides users through a structured 5-stage grilling interview to turn loose, half-formed ideas into razor-sharp, actionable engineering scopes, outputting a downloadable and structured `PRD.md` (Product Requirements Document).

---

## 🌟 Key Features

1. **A2UI Declarative Surfaces**: Emits rich, interactive JSON surfaces (`v0.9.1`) containing choice buttons/chips, radio selectors, progress trackers, text areas, and preview cards rendered natively by A2UI clients (like Gemini Enterprise).
2. **5-Stage Grilling Pipeline**:
   - **Stage 1: Core Problem & Goal (`problem_and_goal`)**: One-sentence commitment, observable problem, and target outcome.
   - **Stage 2: Target Persona & Role (`target_audience`)**: Specific user persona and job-to-be-done.
   - **Stage 3: Current Pain & Workarounds (`pain_and_alternatives`)**: Real friction in current workflows and existing alternatives.
   - **Stage 4: Scope & Non-Goals (`scope_and_non_goals`)**: First concrete 1-week slice vs. explicitly cut non-goals.
   - **Stage 5: PRD Review & Export (`prd_draft`)**: Synthesis of full PRD with export to `PRD.md`.
3. **Downloadable PRD Export**: Dedicated tool generates clean, GitHub-flavored markdown and writes `PRD.md` locally or returns the downloadable artifact surface.
4. **Agent Engine & Gemini Enterprise Ready**: Preconfigured for seamless deployment to Vertex AI Agent Runtime and native registration with Gemini Enterprise using `global` location and ADC credentials (no API key required).

---

## 📂 Project Structure

```
project-ideator/
├── .agent_engine_config.json          # Agent Runtime deployment specification (JSON)
├── .env                               # Local environment configuration (Vertex AI + ADC)
├── .env.example                       # Environment variable templates
├── pyproject.toml                     # Package dependencies and tool settings
├── README.md                          # Documentation and quickstart
├── deployment/
│   ├── agent_engine_config.json       # Agent Runtime deployment specification
│   ├── agent_engine_config.yaml       # Agent Runtime deployment specification (YAML)
│   └── gemini_enterprise_metadata.json# Gemini Enterprise registration metadata
├── project_ideator/
│   ├── __init__.py                    # Exports root_agent
│   ├── a2ui.py                        # A2UI protocol payload builders (v0.9.1)
│   ├── agent.py                       # ADK Agent definition & tool registration
│   ├── config.py                      # Model settings, surface IDs, and catalogs
│   ├── models.py                      # GrillStage enum, PRDSpec, and state models
│   ├── prompt.py                      # System instructions & grilling principles
│   └── tools.py                       # ADK tools for UI rendering and PRD export
└── tests/
    ├── __init__.py
    ├── test_a2ui.py                   # Tests for A2UI protocol messages & envelopes
    ├── test_agent.py                  # Tests for root_agent configuration
    └── test_tools.py                  # Tests for ADK tools & PRD file export
```

---

## 🚀 Local Testing & Verification

### 1. Interactive Custom A2UI Test UI

Run the agent backend and dedicated test UI:

```bash
# Terminal 1: Start ADK backend
uv run adk web --port 8000 .

# Terminal 2: Start A2UI test UI (http://localhost:5173)
cd ui
npm run dev
```

### 2. Built-in ADK Web Dev UI

```bash
uv run adk web .
```

### 3. Interactive CLI Chat

```bash
uv run adk run project_ideator
```

### 3. Run Unit Tests

Execute the test suite using `uv`:

```bash
uv run --extra dev pytest
```

---

## ☁️ Deployment to Agent Engine (Agent Runtime)

Deploy the agent to Vertex AI Agent Runtime using `agents-cli`:

```bash
# Ensure agents-cli is installed
uv tool install google-agents-cli

# Deploy to Agent Runtime
agents-cli deploy --deployment-target agent_runtime
```

---

## 🏢 Publishing to Gemini Enterprise

Once deployed to Agent Runtime, register the agent with Gemini Enterprise:

```bash
agents-cli publish gemini-enterprise \
  --registration-type adk \
  --agent-runtime-id "$AGENT_RUNTIME_ID" \
  --gemini-enterprise-app-id "$GEMINI_ENTERPRISE_APP_ID" \
  --display-name "Project Ideator" \
  --description "Grills software project ideas into crisp engineering scopes and generates PRD.md using A2UI interactive surfaces"
```

---

## 📄 Output PRD Format

The generated `PRD.md` includes:
- **Executive Commitment:** What, for whom, why now.
- **Target Persona & Problem Statement**
- **Current Pain Points & Workarounds**
- **First Slice Core Features (V1)**
- **Non-Goals & Explicit Cuts**
- **Observable Success Metrics ("Done Looks Like")**
- **Riskiest Assumption & Day 1 Milestone**
- **Technical & Architecture Notes**
