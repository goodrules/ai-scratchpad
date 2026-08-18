# AI Location Strategy with Google ADK

A multi-agent AI pipeline for location intelligence and site selection, built with [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and Gemini.

<table>
  <thead>
    <tr>
      <th colspan="2">Key Features</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>🔍</td>
      <td><strong>Multi-Agent Pipeline:</strong> 8 specialized agents for market research, competitor mapping, gap analysis, strategy synthesis, report generation, and interactive map visualization.</td>
    </tr>
    <tr>
      <td>🗺️</td>
      <td><strong>Real-World Data:</strong> Integrates Google Maps Places API for competitor mapping and Google Search for live market research.</td>
    </tr>
    <tr>
      <td>🐍</td>
      <td><strong>Code Execution:</strong> Python/pandas analysis for quantitative gap analysis with viability scoring.</td>
    </tr>
    <tr>
      <td>🎨</td>
      <td><strong>AI-Generated Outputs:</strong> Executive HTML reports and infographics via Gemini's native image generation.</td>
    </tr>
    <tr>
      <td>🖥️</td>
      <td><strong>AG-UI Frontend:</strong> Optional interactive dashboard with <a href="https://docs.ag-ui.com/">AG-UI Protocol</a> and <a href="https://docs.copilotkit.ai/">CopilotKit</a> for real-time pipeline visualization.</td>
    </tr>
    <tr>
      <td>🏗️</td>
      <td><strong>Production-Ready:</strong> Deploy to <a href="https://cloud.google.com/run">Cloud Run</a> or <a href="https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview">Vertex AI Agent Engine</a> via <a href="https://goo.gle/agent-starter-pack">Agent Starter Pack</a>.</td>
    </tr>
  </tbody>
</table>

## What It Does

Given a location and business type (or facility type), this pipeline automatically:

- Researches the market using live web search
- Maps competitors and nearby facilities using Google Maps Places API
- Calculates viability scores with Python code execution
- Generates strategic recommendations with extended reasoning
- Produces an HTML executive report and visual infographic
- Renders an interactive Google Maps visualization of the analysis area

---

## Getting Started: From Zero to Running Agent in 5 Minutes

**Prerequisites:**
- **[Python 3.10-3.13](https://www.python.org/downloads/)**
- **[uv](https://github.com/astral-sh/uv)** (recommended) or pip
- **[Google Maps API key](https://console.cloud.google.com/apis/credentials)** (with Places API enabled)
- **[Node.js 18+](https://nodejs.org/)** *(only required for AG-UI frontend)*

You have two options to get started. Choose the one that best fits your setup:

*   A. **[Google AI Studio (Recommended)](#a-google-ai-studio-recommended)**: The quickest way to get started using a **Google AI Studio API key**. This method involves cloning the sample repository.
*   B. **[Google Cloud Vertex AI](#b-google-cloud-vertex-ai)**: Choose this path if you want to use an existing **Google Cloud project** for authentication and deployment. This method generates a new, prod-ready project using the [agent-starter-pack](https://goo.gle/agent-starter-pack) including all the deployment scripts required.

---

### A. Google AI Studio (Recommended)

You'll need a **[Google AI Studio API Key](https://aistudio.google.com/app/apikey)**.

#### Step 1: Clone Repository
Clone the repository and `cd` into the project directory.

```bash
git clone https://github.com/google/adk-samples.git
cd adk-samples/python/agents/ai-location-strategy
```

#### Step 2: Set Environment Variables
Create a `.env` file in the `app` folder with your API keys (see `.env.example` for reference):

```bash
echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" >> app/.env
echo "GOOGLE_API_KEY=YOUR_AI_STUDIO_API_KEY" >> app/.env
echo "MAPS_API_KEY=YOUR_MAPS_API_KEY" >> app/.env
```

#### Step 3: Install & Run
From the `ai-location-strategy` directory, install dependencies and start the server.

```bash
make install && make dev
```

#### What You'll See

1. Open `http://localhost:8501` in your browser
2. Select **"app"** from the agent dropdown
3. Type a query like: *"I want to open a coffee shop in Indiranagar, Bangalore"*
4. Watch the 8-stage pipeline execute:
   - **Intake** → Extract location and business type
   - **Market Research** → Web search for demographics and trends
   - **Competitor Mapping** → Google Maps Places API for nearby locations
   - **Gap Analysis** → Python code execution for viability scores
   - **Strategy Advisor** → Extended reasoning for recommendations
   - **Report Generator** → HTML executive report
   - **Infographic Generator** → Visual summary image
   - **Map Generator** → Interactive Google Maps visualization

Your agent is now running at `http://localhost:8501`.

---

### B. Google Cloud Vertex AI (via Agent Starter Pack)

Use the [Agent Starter Pack](https://goo.gle/agent-starter-pack) to create a production-ready project with deployment scripts. This is ideal for cloud deployment scenarios.

You'll need: **[Google Cloud SDK](https://cloud.google.com/sdk/docs/install)** and a **Google Cloud Project** with the **Vertex AI API** enabled.

<details>
<summary>📁 Alternative: Using the cloned repository with Vertex AI</summary>

If you've already cloned the repository (as in Option A) and want to use Vertex AI instead of AI Studio, create a `.env` file in the `app` folder with:

```bash
echo "GOOGLE_GENAI_USE_VERTEXAI=TRUE" >> app/.env
echo "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID" >> app/.env
echo "GOOGLE_CLOUD_LOCATION=us-central1" >> app/.env
echo "MAPS_API_KEY=YOUR_MAPS_API_KEY" >> app/.env
```

Make sure you're authenticated with Google Cloud:
```bash
gcloud auth application-default login
```

Then run `make install && make dev` to start the agent.
</details>

#### Step 1: Create Project from Template
This command uses the [Agent Starter Pack](https://goo.gle/agent-starter-pack) to create a new directory (`my-location-agent`) with all the necessary code.
```bash
# Create and activate a virtual environment
python -m venv .venv && source .venv/bin/activate # On Windows: .venv\Scripts\activate

# Install the starter pack and create your project
pip install --upgrade agent-starter-pack
agent-starter-pack create my-location-agent -a adk@ai-location-strategy
```
<details>
<summary>⚡️ Alternative: Using uv</summary>

If you have [`uv`](https://github.com/astral-sh/uv) installed, you can create and set up your project with a single command:
```bash
uvx agent-starter-pack create my-location-agent -a adk@ai-location-strategy
```
This command handles creating the project without needing to pre-install the package into a virtual environment.
</details>

You'll be prompted to select a deployment option (Agent Engine or Cloud Run) and verify your Google Cloud credentials.

#### Step 2: Install & Run
Navigate into your **newly created project folder**, then install dependencies and start the server.
```bash
cd my-location-agent && make install && make dev
```
Your agent is now running at `http://localhost:8501`.

## Cloud Deployment

> **Note:** Cloud deployment applies only to projects created with **agent-starter-pack** (Option B).

**Prerequisites:**
```bash
gcloud components update
gcloud config set project YOUR_PROJECT_ID
```

Deploy with the built-in [adk-web](https://github.com/google/adk-web) interface:

```bash
make deploy IAP=true
```

After deployment, grant users access to your IAP-protected service by following the [Manage User Access](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run#manage_user_or_group_access) documentation.

For production deployments with CI/CD, see the [Agent Starter Pack Development Guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/development-guide.html#b-production-ready-deployment-with-ci-cd).

---

## Agent Details

| Attribute | Description |
| :--- | :--- |
| **Interaction Type** | Workflow |
| **Complexity** | Advanced |
| **Agent Type** | Multi Agent (Sequential Pipeline) |
| **Components** | Multi-agent, Function calling, Web search, Google Maps API, Code execution, Image generation |
| **Vertical** | Location Intelligence |

<p align="center">
  <img src="assets/images/agent-flow.png" alt="Agent Flow and Tool Integration" width="700">
</p>

## Model Configuration

This agent supports multiple Gemini model families. Edit `app/config.py` to switch models based on your access and quota:

| Model Option | Text Models | Image Model | Notes |
|--------------|-------------|-------------|-------|
| **Option 1: Gemini 2.5 Pro** | `gemini-2.5-pro` | `gemini-3-pro-image-preview` | **Recommended** - Stable, production-ready |
| **Option 2: Gemini 3.1 Pro Preview** | `gemini-3.1-pro-preview` | `gemini-3-pro-image-preview` | Latest features - may throw 503 "model overloaded" errors |
| **Option 3: Gemini 3 Flash Preview** | `gemini-3.7-flash` | `gemini-3.7-flash` | Fastest, lowest cost |

**Gemini 3 Documentation:**
- [Vertex AI - Get started with Gemini 3](https://cloud.google.com/vertex-ai/generative-ai/docs/start/get-started-with-gemini-3)
- [Google AI - Gemini 3 API](https://ai.google.dev/gemini-api/docs/gemini-3)

To switch models, uncomment the desired option in `app/config.py`:

```python
# app/config.py

# Option 1: Gemini 2.5 Pro (RECOMMENDED - stable, good for production)
# FAST_MODEL = "gemini-2.5-pro"
# PRO_MODEL = "gemini-2.5-pro"
# ...

# Option 2: Gemini 3.1 Pro Preview (latest features, may have availability issues)
FAST_MODEL = "gemini-3.7-flash"
PRO_MODEL = "gemini-3.7-flash"
CODE_EXEC_MODEL = "gemini-3.7-flash"
IMAGE_MODEL = "gemini-3.1-flash-image"
```

> **Note:** If you encounter `503 UNAVAILABLE - model overloaded` errors, switch to Gemini 2.5 Pro for better reliability.

---

## AG-UI Frontend (Optional)

Want a richer experience beyond the default ADK web UI? This agent includes an optional **[AG-UI Protocol](https://docs.ag-ui.com/)** frontend built with [CopilotKit](https://docs.copilotkit.ai/) that provides:

- **Real-time Pipeline Timeline**: Watch the 8-stage analysis unfold with collapsible steps
- **Generative UI**: Rich visualizations appear in the chat as the agent works
- **Interactive Dashboard**: Location scores, competitor stats, market characteristics
- **Bidirectional State Sync**: Frontend and ADK agent share state in real-time

<p align="center">
  <img src="assets/images/ag-ui-sync.png" alt="AG-UI Bidirectional State Sync" width="650">
</p>

### Quick Start

```bash
# First time: Install frontend dependencies
make ag-ui-install

# Run both backend and frontend servers
make ag-ui
```

This starts:
- **Backend** at `http://localhost:8000` (FastAPI + ADK agent)
- **Frontend** at `http://localhost:3000` (Next.js + CopilotKit)

Open `http://localhost:3000` to see the interactive dashboard.

<details>
<summary>Manual Setup (Alternative)</summary>

```bash
# Terminal 1: Start the backend
cd app/frontend/backend
pip install -r requirements.txt
python main.py
# Runs at http://localhost:8000

# Terminal 2: Start the frontend
cd app/frontend
npm install
cp .env.local.example .env.local
npm run dev
# Runs at http://localhost:3000
```
</details>

See [app/frontend/README.md](app/frontend/README.md) for detailed frontend documentation.

---

## Example Prompts

| Region | Location | Use Case | Example Prompt |
|--------|----------|----------|----------------|
| Asia | Bangalore, India | Coffee Shop | "I want to open a coffee shop in Indiranagar, Bangalore" |
| Asia | Hyderabad, India | Data Center | "I'm interested in building a hyperscale data center in Southern India" |
| Asia | Tokyo, Japan | Ramen Restaurant | "Analyze Shibuya, Tokyo for opening a ramen restaurant" |
| Asia | Singapore | Bubble Tea | "Where should I open a bubble tea shop in Orchard Road, Singapore?" |
| Americas | Austin, Texas | Fitness Studio | "Where should I open a fitness studio in Austin, Texas?" |
| Americas | Virginia, USA | Data Center | "Analyze Northern Virginia for a new colocation data center campus" |
| Americas | Mexico City | Taco Restaurant | "Analyze Roma Norte, Mexico City for a taco restaurant" |
| Americas | Toronto, Canada | Craft Brewery | "Help me find a location for a craft brewery in Toronto's Distillery District" |
| Europe | London, UK | Bookstore Cafe | "Help me find the best location for a bookstore cafe in Shoreditch, London" |
| Europe | Berlin, Germany | Vegan Restaurant | "Analyze Berlin's Kreuzberg for opening a vegan restaurant" |
| Middle East | Dubai, UAE | Bakery | "I'm planning to open a bakery in Dubai Marina" |
| Oceania | Sydney, Australia | Juice Bar | "Analyze the market for a juice bar in Bondi Beach, Sydney" |

---

## Architecture

<p align="center">
  <img src="assets/images/pipeline-architecture.png" alt="Pipeline Architecture" width="700">
</p>

The pipeline is built as a `SequentialAgent` that orchestrates 8 specialized sub-agents, each handling a specific phase of the analysis.

### State Flow

Each agent reads from and writes to a shared session state, enabling seamless data flow between stages:

<p align="center">
  <img src="assets/images/data-flow.png" alt="Data Flow Between Agents" width="650">
</p>

---

## Project Structure

```
ai-location-strategy/
├── Makefile                          # Build and run commands
├── pyproject.toml                    # Dependencies and package config
├── .env.example                      # Environment template
├── README.md                         # This file
│
└── app/                              # Agent package (exported as root_agent)
    ├── __init__.py                   # Exports root_agent for ADK discovery
    ├── agent.py                      # SequentialAgent pipeline definition
    ├── config.py                     # Model selection and retry config
    ├── .env                          # Environment variables (from .env.example)
    │
    ├── sub_agents/                   # 8 specialized agents
    │   ├── intake_agent/             # Parse location and business type
    │   ├── market_research/          # Live web search for market data
    │   ├── competitor_mapping/       # Google Maps Places API
    │   ├── gap_analysis/             # Python code execution, viability scores
    │   ├── strategy_advisor/         # Extended reasoning, recommendations
    │   ├── report_generator/         # HTML executive report
    │   ├── infographic_generator/    # AI-generated visual summary
    │   └── map_generator/            # Interactive Google Maps visualization
    │
    ├── tools/                        # Custom function tools
    │   ├── places_search.py          # Google Maps Places API
    │   ├── html_report_generator.py  # Executive report generation
    │   ├── image_generator.py        # Infographic generation
    │   └── map_generator.py          # Interactive map generation
    │
    ├── schemas/                      # Pydantic output schemas
    ├── callbacks/                    # Pipeline lifecycle callbacks
    └── frontend/                     # AG-UI interactive dashboard
```

---

## Troubleshooting

- **503 model overloaded**: Switch to Gemini 2.5 Pro (Option 1) in `app/config.py`
- **Maps API errors**: Ensure Places API is enabled for your Maps API key
- **Auth errors**: Verify `GOOGLE_API_KEY` (AI Studio) or `gcloud auth application-default login` (Vertex AI)
- [ADK Documentation](https://google.github.io/adk-docs/)
- [Vertex AI Authentication Guide](https://cloud.google.com/vertex-ai/docs/authentication)

---

## Authors

Developed by [Mike Goodman](https://github.com/goodrules), based on the original [AI Location Strategy ADK sample](https://github.com/google/adk-samples) and [Retail AI Location Strategy notebook](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/use-cases/retail/retail_ai_location_strategy_gemini_3.ipynb) by [Lavi Nigam](https://github.com/lavinigam-gcp) and [Deepak Moonat](https://github.com/dmoonat).

---

## Disclaimer

This agent sample is provided for illustrative purposes only. It serves as a basic example of an agent and a foundational starting point for individuals or teams to develop their own agents.

Users are solely responsible for any further development, testing, security hardening, and deployment of agents based on this sample. We recommend thorough review, testing, and the implementation of appropriate safeguards before using any derived agent in a live or critical system.

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
