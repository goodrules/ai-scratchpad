# Agents & Multi-Agent Systems on Vertex AI

Working, readable, copy-pasteable reference implementations of autonomous AI agents and multi-agent workflows using Google's **Agent Development Kit (ADK)** and **Vertex AI Agent Engine**.

All agents and evaluation scripts authenticate via Google Cloud **Application Default Credentials (ADC)** (`gcloud auth application-default login`) — no third-party API keys required.

---

## Directory Layout

```
agents/
├── adk/
│   ├── adk_guide/                 # Progressive workshop tutorial & foundational agents
│   │   ├── simple_tutorial.md     # Step-by-step engineering workshop guide
│   │   ├── my_first_agent/        # Basic single agent with custom Python tools
│   │   ├── my_2_agent/            # Agent with multi-tool capabilities
│   │   ├── workflow_agent_seq/    # Sequential multi-agent workflow
│   │   └── mcp_test_agent/        # Agent with Model Context Protocol (MCP) file system
│   │
│   └── agents/                    # Production-style multi-agent architectures
│       ├── google_search_agent/   # Grounded web research agent
│       ├── short_story_agent/     # Cyclic Writer-Editor-Refiner pipeline workflow
│       ├── doc_understanding/     # Multimodal document loader & localized citations
│       ├── travel-concierge/      # Multi-agent hierarchical concierge with Cloud Trace
│       ├── software-bug-assistant/# Bug triage with code execution & Cloud SQL/Postgres
│       └── ai-location-strategy/  # Spatial intelligence analysis pipeline
│
└── demos/                         # Platform evaluation & runtime services
    ├── eval_sea_captain_local.py  # Local evaluation using Vertex AI EvalTask
    ├── eval_sea_captain_ae_deploy.py # Remote deploy to Vertex AI Agent Engine + evals
    └── memorybank_interactive.py  # Interactive Memory Bank session management
```

---

## Quick Start

### 1. Prerequisites & Auth

```bash
uv sync                                    # Install dependencies from repository root
gcloud auth application-default login      # Authenticate via ADC
```

Set environment variables in your active shell or copy `.env.example`:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="global"              # Use "us-central1" for EvalTask, Agent Engine, or Memory Bank
export GOOGLE_GENAI_USE_VERTEXAI="TRUE"
```

---

## Running the Agents

### A. Run via ADK CLI (Terminal)

Interact with any ADK agent directly in your terminal:

```bash
# Run the basic tutorial utility agent
uv run adk run agents/adk/adk_guide/my_first_agent

# Run the Google Search agent
uv run adk run agents/adk/agents/google_search_agent/app

# Run the Short Story pipeline workflow
uv run adk run agents/adk/agents/short_story_agent
```

### B. Run via ADK Web UI (Browser)

Launch the interactive local web interface to visualize agent execution graphs, inspect state, and test conversations:

```bash
cd agents/adk/agents
uv run adk web
```

Then navigate to `http://localhost:8000` (or the port displayed in your terminal).

---

## Agent Catalog

| Agent / System | Directory | Architecture | Key Capabilities |
| :--- | :--- | :--- | :--- |
| **My First Agent** | [`adk/adk_guide/my_first_agent/`](adk/adk_guide/my_first_agent/) | Single `Agent` | Custom Python function tools, input validation, temperature conversion. |
| **Workflow Agent** | [`adk/adk_guide/workflow_agent_seq/`](adk/adk_guide/workflow_agent_seq/) | Sequential `Workflow` | Multi-step agent handoff pipeline. |
| **MCP File Agent** | [`adk/adk_guide/mcp_test_agent/`](adk/adk_guide/mcp_test_agent/) | MCP Integration | Model Context Protocol (`@modelcontextprotocol/server-filesystem`). |
| **Google Search Agent** | [`adk/agents/google_search_agent/`](adk/agents/google_search_agent/) | Grounded `Agent` | Native real-time web search grounding via `google_search` tool. |
| **Short Story Pipeline** | [`adk/agents/short_story_agent/`](adk/agents/short_story_agent/) | State Graph `Workflow` | Planner $\to$ Writer $\to$ Editor $\to$ Refiner loop with conditional exit. |
| **Document Understanding** | [`adk/agents/doc_understanding/`](adk/agents/doc_understanding/) | Multimodal `Agent` | Custom `LoadFileTool` streaming raw document bytes into Gemini inline parts. |
| **Travel Concierge** | [`adk/agents/travel-concierge/`](adk/agents/travel-concierge/) | Hierarchical Sub-Agents | Multi-specialist routing (planning, booking, in-trip, post-trip) + Cloud Trace. |
| **Software Bug Assistant** | [`adk/agents/software-bug-assistant/`](adk/agents/software-bug-assistant/) | Specialist + Code Exec | Triage agent delegating to code executor subagent; Cloud SQL or local Postgres. |
| **AI Location Strategy** | [`adk/agents/ai-location-strategy/`](adk/agents/ai-location-strategy/) | Multi-Stage Pipeline | Demographics, competition, and traffic analysis for retail site selection. |

---

## Platform Evaluation & Agent Engine Demos

The `agents/demos/` folder demonstrates enterprise platform integrations on Vertex AI:

### 1. Local Agent Evaluation ([`eval_sea_captain_local.py`](demos/eval_sea_captain_local.py))
Evaluates an agent against a golden dataset using Vertex AI's native `EvalTask` across relevance and tool-use metrics:
```bash
uv run python agents/demos/eval_sea_captain_local.py
```

### 2. Remote Agent Engine Deployment ([`eval_sea_captain_ae_deploy.py`](demos/eval_sea_captain_ae_deploy.py))
Packages and deploys an ADK agent to the managed serverless **Vertex AI Agent Engine**, runs remote evaluation via `client.evals`, and tears down resources:
```bash
uv run python agents/demos/eval_sea_captain_ae_deploy.py --staging-bucket gs://your-staging-bucket
```

### 3. Long-Term Memory Bank ([`memorybank_interactive.py`](demos/memorybank_interactive.py))
Demonstrates persistent context and custom memory topics across interactive sessions using `VertexAiMemoryBankService`:
```bash
uv run python agents/demos/memorybank_interactive.py
```

---

## Observability

All production agents in this directory support OpenTelemetry tracing exported directly to **Google Cloud Trace** via `opentelemetry-exporter-gcp-trace`. Traces automatically capture agent handoffs, subagent delegations, tool calls, and model latency without vendor lock-in.
