# Google Cloud Agent Gateway — Hybrid Enterprise Demo
## Live Evolution & Blind Critic Benchmark Tracker

This live tracker documents the iterative construction and blind evaluation of the **Google Cloud Agent Gateway Hybrid Demo** against the official Google Cloud reference bar ([agent-starter-pack](https://github.com/GoogleCloudPlatform/agent-starter-pack) + [Enterprise Agent Governance Codelab](https://codelabs.developers.google.com/enterprise-agent-governance-sgp)).

---

### Demo Architecture & 5 Governance Pillars

| Pillar | How Demonstrated in Demo |
| :--- | :--- |
| **1. Agent Identity** | Cryptographic agent identity token verification (`service-<project-num>@gcp-sa-aiplatform-re...` / SPIFFE claims), preventing rogue agent impersonation. |
| **2. Agent Registry** | Tool discovery cataloging (`agentregistry.googleapis.com`), dynamic MCP spec ingestion (`toolspec.json`), and service endpoint allowlisting. |
| **3. IAM Unified Access Policies** | Granular ingress/egress policy bindings (`roles/iap.egressor`, `roles/agentgateway.serviceAgent`, `roles/run.servicesInvoker`) restricting tool access. |
| **4. Model Armor** | Boundary payload sanitization (`modelarmor.googleapis.com`), prompt injection detection, sensitive data/PII masking, and malicious input filtering. |
| **5. Semantic Governance Policies (SGP)** | Natural language constraint evaluation (`"Block any transfer value exceeding USD 1000."`) evaluated via LLM-as-judge over Private Service Connect (PSC). |

---

### Component Evolution & Blind Critic Scorecard

| Piece | Scope | Builder Status | Critic Verdict (Blind) | Remaining Gap / Action |
| :--- | :--- | :--- | :--- | :--- |
| **Piece 1** | Synthetic Enterprise Data & FastMCP Server | 🟢 Complete (23 tests passing) | 🏆 **Candidate Alpha WON (100% Unanimous)** | Implemented cumulative daily limit tracking & verified. Clean! |
| **Piece 2** | Custom Governed ADK Agent | 🟢 Complete (36 tests passing) | 🏆 **Candidate Alpha WON (100% Unanimous)** | Fixed Agent Registry resource path canonicalization & added runner. |
| **Piece 3** | Gateway & Policy Automation (GCP + Hybrid Simulator) | 🟢 Complete (46 tests passing) | 🏆 **Candidate Alpha WON (100% Unanimous)** | Decoupled declarative JSON policies dynamically & fixed root packaging. |
| **Piece 4** | Interactive Visual UI (Gateway Inspection Dashboard) | 🟢 Complete (21 tests passing) | 🏆 **Candidate Alpha WON (100% Unanimous)** | Added SSE streaming, multi-turn session memory, conversational intent & dual-mode! |
| **Piece 5** | Customer Walkthrough & Exec README | 🟢 Complete (127 total tests passing) | 🏆 **Candidate Alpha WON (100% Unanimous)** | Added standalone FastMCP Dockerfile, --deploy-mcp flag, and full compliance mapping! |

---

### Detailed Critic Review Log

#### Piece 1: Synthetic Data & MCP Server
- **Candidate Alpha (Ours)** vs **Candidate Beta (Google Codelab Bar)**
- **Blind Critic Verdict**: **Winner: Candidate Alpha (Ours)**
- **Scorecard Analysis**:
  * *Simplicity*: Alpha avoids Beta's 103 lines of brittle ASGI stream-intercepting middleware hacks (`AcceptHeaderFixMiddleware`, `SseFixMiddleware`) and uses native FastMCP custom routes (`/tools`, `/toolspec.json`).
  * *Clarity*: Alpha provides clean dataclasses/TypedDicts, explicit return status codes, and type-safe error payloads.
  * *Enterprise Realism*: Alpha has 10 accounts across 3 distinct tiers (Standard, Premium VIP, Corporate Treasury), AML risk scores, and phone normalization.
  * *Data Integrity*: Beta had a critical bug where transfers silently destroyed money (debited sender but never credited recipient!). Alpha uses an atomic thread-safe ledger (`RLock`) that properly debits sender and credits recipient.
  * *Verifiability*: Alpha: 23 automated tests covering unit, edge-case, and HTTP Starlette integration (0.014s). Beta: 0 automated tests.
- **Micro-Polish Applied**: Added cumulative 24-hour daily spend checking (`get_daily_spent`) and disambiguated alias collision.

#### Piece 2: Custom Governed ADK Agent
- **Candidate Alpha (Ours)** vs **Candidate Beta (Google Codelab Bar)**
- **Blind Critic Verdict**: **Winner: Candidate Alpha (Ours)**
- **Scorecard Analysis**:
  * *Simplicity & Robustness*: Alpha runs decoupled locally or in cloud without crashing on import; Beta crashed with collection errors due to unconditional root-level GCP credential and Agent Registry calls.
  * *Architecture & Factoring*: Alpha cleanly partitions `prompts.py`, `agent.py`, `__init__.py`, and provides a dependency-injection `create_agent()` factory; Beta is a monolithic 79-line script with hardcoded environment mutations and zero DI.
  * *Governance Awareness*: Alpha implements dedicated Step 6 instructions and error recovery for SGP-01 AML velocity limits, Model Armor prompt injection protection, and IAM access blocks; Beta has zero governance awareness and hallucinates or crashes upon policy denials.
  * *Financial Guardrails*: Alpha enforces a 6-step lifecycle with verified phone lookups and tested $50 confirmation gates with explicit Y/N branching; Beta has unverified prompt text with zero tests.
  * *Verifiability*: Alpha: 36 automated unit, schema, hybrid resolution, and multi-turn runner tests (0.88s). Beta: Dead on arrival (pytest collection failure).
- **Critic Polish Applied**:
  * Canonicalized `server_name` in `_get_registry_banking_tools` to standard GCP resource format: `projects/{project_id}/locations/{location}/mcpServers/{server_name}`.
  * Added `test_registry_resource_name_canonicalization` to verify all resource formats.
  * Added `run_tests.py` convenience runner for running the full 59-test suite from any directory.

#### Piece 3: Gateway & Policy Automation
- **Candidate Alpha (Ours)** vs **Candidate Beta (Google Codelab Bar)**
- **Blind Critic Verdict**: **Winner: Candidate Alpha (Ours)**
- **Scorecard Analysis**:
  * *Developer Experience & Speed*: Alpha provides a self-contained in-memory and HTTP ASGI simulator running all 5 governance steps in **0.85 seconds**; Beta requires $\ge 25$ minutes of live GCP provisioning before any policy can be tested.
  * *Architectural Completeness*: Alpha implements all 5 pillars with real enforcement and error codes (401 Identity, 404 Registry, 403 Model Armor, 403 IAM, 403 SGP AML & velocity); Beta leaves Pillars 1, 3, and 5 without automated verification or runtime rules.
  * *Safety & Teardown*: Alpha provides fully parameterized scripts with `--dry-run` and clean reverse-dependency teardown (`destroy_gcp.sh`); Beta has zero teardown script (causing VPC resource leaks) and no dry-run capability.
  * *Verifiability*: Alpha: 46 automated unit, integration, and syntax tests (100% passing). Beta: 0 tests.
- **Critic Polish Applied**:
  * Added dynamic JSON policy loading (`load_policies_from_dir`) into `GatewaySimulator` so declarative files (`sgp_aml_policy.json`, `model_armor_policy.json`, `iap_access_policy.json`) drive runtime enforcement directly rather than hardcoded logic.
  * Updated relative imports in `gateway/__init__.py` and created root `agents/__init__.py`, `agents/platform/__init__.py`, and `agents/platform/agent-gateway/__init__.py` package markers so root execution (`uv run python agents/platform/agent-gateway/gateway/test_gateway.py`) works out-of-the-box.
  * Expanded platform test suite to **105 tests running in 1.75s, 100% passing**.

#### Piece 4: Interactive Visual UI (Gateway Inspection Dashboard)
- **Candidate Alpha (Ours)** vs **Candidate Beta (Google Codelab Bar)**
- **Blind Critic Verdict**: **Winner: Candidate Alpha (Ours)**
- **Scorecard Analysis**:
  * *Customer Compelling Value*: Alpha delivers an interactive 3-column enterprise dashboard with live multi-turn chat, 1-click demo scenario presets, real-time 5-pillar waterfall timeline, dynamic policy toggles, AML limit sliders, and collapsible JSON inspection drawers; Beta provided ZERO frontend UI (only headless CLI SSE chunks requiring terminal curls or GCP Cloud Logging).
  * *Simplicity & Zero Friction*: Alpha uses pure native HTML5/CSS/ES6+ JavaScript with zero build tools (`no node_modules`, `no vite`, `no npm`), served directly by FastAPI and booting in < 1 second; Beta requires complex Agent Platform scaffolding.
  * *Verifiability*: Alpha: 21 automated tests covering all endpoints, 7 scenarios, policy toggling, slider thresholds, session memory, and streaming audit events. Beta: 0 UI tests.
- **Critic Polish Applied**:
  * Added **Dual-Mode Execution** in `app.py` (`simulated` vs `live_adk`) enabling optional live inference via Vertex AI / Gemini ReAct loop while providing deterministic sub-millisecond local simulation.
  * Implemented conversational intent resolution for general inquiries (rates, guidelines, greetings) avoiding unnecessary dummy tool execution.
  * Added **Multi-Turn Session Memory** in `_SESSION_STORE` accessible via `/api/chat/history?session_id=...`.
  * Implemented **Server-Sent Events (SSE)** streaming via `/api/audit/stream` with test-friendly termination (`max_events`), initial connection frame, and frontend fallback.
  * Expanded full platform test suite to **126 tests running in 1.74s, 100% passing**.

#### Piece 5: Customer Walkthrough & Executive Documentation
- **Candidate Alpha (Ours)** vs **Candidate Beta (Google Codelab Bar)**
- **Blind Critic Verdict**: **Winner: Candidate Alpha (Ours — 100% Unanimous)**
- **Scorecard Analysis**:
  * *Executive Clarity & Value*: Alpha formulates the "Missing Perimeter in Generative AI" problem with mathematical clarity, threat vector analysis, and formal regulatory compliance mapping (SOC 2 Type II, PCI-DSS v4.0, Bank Secrecy Act / AML, EU AI Act, NIST AI RMF). Beta provided a 2-sentence description with zero compliance mapping.
  * *Time to Value & Developer Onboarding*: Alpha launches locally in < 60s with 0ms cloud dependency and 127 automated tests passing in 2.2s. Beta crashed during test collection with missing GCP credentials and required 45+ minutes of live GCP provisioning before anything could be tested.
  * *Breadth of Governance Architecture*: Alpha covers all 5 pillars with exact HTTP status codes (401, 404, 403), sequence flows, error payloads, and failure tests. Beta only covered SGP, had broken file links, and leaked author filesystem paths.
  * *Customer Demo Walkthrough Quality*: Alpha provides 7 turnkey scenarios with exact inputs, customer personas, executive talking points, visual waterfall outputs, and risk context, plus live UI sliders. Beta had a single manual 3-turn playground test.
  * *Operational Completeness & Safety*: Alpha provides dry-run, parameterized deployment, and dedicated teardown script (`destroy_gcp.sh`). Beta had zero teardown script, leaving orphaned cloud resources.
- **Critic Polish Applied**:
  * Added standalone `Dockerfile` and `pyproject.toml` in `agents/platform/agent-gateway/mcp_server/` for production containerization on Python 3.11-slim with `uv`.
  * Added `--deploy-mcp` single-command deployment flag to `gateway/deploy_gcp.sh` to build and deploy FastMCP directly to Cloud Run and resolve its live URL.
  * Added automated unit test `test_deploy_gcp_with_deploy_mcp_dry_run` to `gateway/test_gateway.py`.
  * Expanded platform test suite to **127 tests running in 2.22s, 100% passing**.

---

### Current Milestone Log

* **16:35** — Initialized task workspace. Fetched live codelab (`enterprise-agent-governance-sgp`) and cloned official `agent-starter-pack` repository.
* **16:37** — Defined parallel subagents (`platform-builder` and `blind-critic`).
* **16:38** — Initialized Live Progress Page.
* **16:47** — **Piece 1 Builder Completed**: Built `data.py`, `server.py`, `test_mcp.py`.
* **16:51** — **Piece 1 Blind Critic Delivered**: Candidate Alpha won unconditionally.
* **16:54** — Enhanced cumulative daily spend tracking; 23 tests passing in 0.014s.
* **16:55** — Installed `google-adk[agent-identity]` dependency. Launched `platform-builder` for Piece 2 (Custom Governed ADK Agent).
* **17:05** — **Piece 2 Builder Completed**: Built `prompts.py`, `agent.py`, `test_agent.py` (35 unit and integration tests passing in 0.801s).
* **17:08** — **Piece 2 Blind Critic Delivered**: Candidate Alpha won unconditionally against the reference bar.
* **17:09** — Remediated critic gap: Canonicalized Agent Registry resource path, added unit test, and built `run_tests.py`. 59 tests passing in 0.872s.
* **17:11** — Launched `platform-builder` for Piece 3 (Gateway & Policy Automation: GCP Deployment Scripts + Hybrid Local Simulator).
* **17:22** — **Piece 3 Builder Completed**: Built `simulator.py`, `deploy_gcp.sh`, `destroy_gcp.sh`, declarative `policies/`, and `test_gateway.py`.
* **17:26** — **Piece 3 Blind Critic Delivered**: Candidate Alpha won unconditionally against the reference bar.
* **17:29** — Remediated critic gap: Added dynamic policy loading from disk, updated relative imports, added package markers. All 105 tests passing in 1.75s.
* **17:35** — Launched `platform-builder` for Piece 4 (Interactive Visual UI: Gateway Inspection Dashboard).
* **17:42** — **Piece 4 Builder Completed**: Built `app.py`, `index.html`, `dashboard.css`, `dashboard.js`, `test_ui.py`. 122 tests passing in 1.80s.
* **17:45** — **Piece 4 Blind Critic Delivered**: Candidate Alpha won unconditionally against Candidate Beta.
* **20:47** — Launched `platform-builder` for Piece 5 (Customer Walkthrough & Exec README).
* **20:52** — **Piece 5 Builder Completed**: Built executive README (`agents/platform/agent-gateway/README.md`) featuring 5 governance pillars, architectural diagrams, 60-second quickstart, 7 detailed demo scenarios, production GCP deployment guide, regulatory compliance mapping (SOC 2, PCI-DSS, AML/BSA, EU AI Act, NIST AI RMF), and codebase directory map.
* **20:54** — **Piece 5 Blind Critic Delivered**: Candidate Alpha won unconditionally across all 5 evaluation dimensions.
* **20:57** — Remediated critic gap: Built `mcp_server/Dockerfile`, `mcp_server/pyproject.toml`, added `--deploy-mcp` to `deploy_gcp.sh`, added dry-run verification test, updated documentation.
* **20:58** — **FULL PLATFORM VERIFIED: All 5 Pieces Won Blind Unanimously. 127/127 tests passing in 2.22s.** Ready for customer presentation!
* **21:10** — Model Upgrade: Updated all ADK agent model configurations and test expectations to use `'gemini-3.8-flash'` exclusively. 127/127 tests passing.



