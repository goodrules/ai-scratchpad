# ADK Engineering Workshop: Building Agentic Systems with Vertex AI

**Objective:** By the end of this guide, you will have a working environment for the Google Agent Development Kit (ADK), created your first agent, connected it to external tools (including the Model Context Protocol), and orchestrated complex workflows.

**Target Model:** `gemini-3.7-flash`
**Platform:** Google Cloud Vertex AI

-----

## 1. Environment Setup & Authentication

ADK is model-agnostic but optimized for the Google ecosystem. We will configure it to use Vertex AI as the inference provider.

### **Prerequisites**

  * Python 3.10+
  * Node.js & `npx` (Required for the MCP example later)
  * A Google Cloud Project with the **Vertex AI API** enabled.

### **Terminal Configuration**

Run the following commands to install the SDK and set up authentication using Application Default Credentials (ADC).

```bash
# 1. Install the ADK
pip install google-adk

# 2. Authenticate with Google Cloud
gcloud auth application-default login

# 3. Set Environment Variables
# These tell ADK to route requests to Vertex AI instead of Google AI Studio
export GOOGLE_CLOUD_PROJECT="your-project-id" # <--- Update this
export GOOGLE_CLOUD_LOCATION="global"         # <--- Update this
export GOOGLE_GENAI_USE_VERTEXAI=true

# To make these permanent, add to ~/.bashrc or ~/.zshrc
```

-----

## 2. Bootstrapping: The "Hello World" Agent

The ADK CLI provides scaffolding to get you started instantly.

### **Create the Project**

```bash
adk create my_first_agent
cd my_first_agent
ls  # Should see agent.py, __init__.py, etc.
```
*Ensure the agent name includes only letters, numbers, or underscores.*

### **Configure the Agent**

Open `my_first_agent/agent.py`. This is your entry point. We will configure the root agent to use the Gemini 3 Pro Preview model.

```python
from google.adk import Agent

root_agent = Agent(
    name="helper_agent",
    model="gemini-3.7-flash",
    description="A helpful assistant for engineering tasks.",
    instruction="You are a helpful AI assistant. Answer queries concisely and technically.",
)
```

**Note:** `Agent` and `LlmAgent` are equivalent in ADK. Both refer to LLM-powered agents that use language models for reasoning and decision-making.

**IMPORTANT:** When using `adk run` or `adk web`, the agent variable **must** be named `root_agent`. The ADK CLI tools are hardcoded to look for this specific variable name in your `agent.py` file. While you can use any variable name when calling agents programmatically in Python, the CLI requires `root_agent`.

### **Run the Agent**

Interact with your agent immediately via the CLI:

```bash
adk run my_first_agent
```

OR using the built-in web UI:
```bash
adk web
```
*When running adk web or adk run, make sure you are in the parent folder to the newly created agent folder (e.g. my_first_agent folder).*

-----

## 3. Adding Capabilities: Tools & Grounding

Agents need to interact with the world. We will explore three ways to give your agent tools: **Python Functions**, **Native Tools**, and **MCP**.

### **A. Custom Python Functions**

You can pass standard Python functions directly to the agent.

```python
# In agent.py
from google.adk import Agent

# 1. Define the tool
def convert_temperature(value: float, from_scale: str, to_scale: str) -> float:
    """Converts temperatures between 'C', 'F', and 'K'."""
    # Validate inputs
    if not from_scale or not to_scale:
        raise ValueError("Scale parameters cannot be empty")

    # Normalize inputs to first letter uppercase (e.g. 'fahrenheit' -> 'F')
    from_scale = from_scale[0].upper()
    to_scale = to_scale[0].upper()

    # Validate scale types
    if from_scale not in ['C', 'F', 'K'] or to_scale not in ['C', 'F', 'K']:
        raise ValueError("Scales must be 'C', 'F', or 'K'")

    if from_scale == to_scale:
        return value

    # Normalize to Celsius
    celsius = value
    if from_scale == 'F':
        celsius = (value - 32) * 5 / 9
    elif from_scale == 'K':
        celsius = value - 273.15

    # Convert to target
    if to_scale == 'F':
        return (celsius * 9 / 5) + 32
    elif to_scale == 'K':
        return celsius + 273.15
    return celsius

# 2. Register it
root_agent = Agent(
    name="utility_agent",
    model="gemini-3.7-flash",
    instruction="You are a utility assistant. Use 'convert_temperature' to answer queries. Understand that 'F' and 'Fahrenheit', 'C' and 'Celsius', 'K' and 'Kelvin' are interchangeable.",
    tools=[convert_temperature]
    # Note: 'description' parameter is primarily used for multi-agent routing
)
```

### **B. Grounding with Google Search**

For research tasks, use the built-in `GoogleSearchTool` to prevent hallucinations and access real-time data.

```python
from google.adk import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="researcher",
    model="gemini-3.7-flash",
    instruction="You are a researcher. Use Google Search to find citations.",
    tools=[google_search]
)
```

### **C. The Model Context Protocol (MCP)**

MCP is a standard for connecting AI models to external systems (databases, file systems, GitHub) without writing custom wrappers. We will use the **File System MCP Server** to let the agent read/write files.

**Requirements:** Ensure `npx` is installed.

First, create a test workspace folder from the root directory:
```bash
mkdir workspace
```

Now, update the agent.py file:

```python
import os
from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# 1. Setup a safe workspace directory
allowed_dir = os.path.abspath("./workspace")
if not os.path.exists(allowed_dir):
    os.makedirs(allowed_dir)

# 2. Configure the MCP Toolset (Runs the server via npx)
fs_mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", allowed_dir],
        )
    )
)

# 3. Create the Agent
root_agent = Agent(
    name="fs_agent",
    model="gemini-3.7-flash",
    instruction="""
    You are a file system assistant.
    You can read/write files in the workspace.
    Always verify file content after writing.
    """,
    tools=[fs_mcp_toolset]
)
```

-----

## 4. Orchestration: Multi-Agent Workflows

For complex tasks, single agents often fail to maintain context or adhere to steps. ADK uses **Workflow** graphs to chain multiple agents and nodes together.

### **A. Sequential Workflow (The Pipeline)**

*Pattern: Output of Agent A becomes Input of Agent B.*

**Scenario:** A **Researcher** finds information using Google Search, and a **Writer** formats it into a report.

```python
from google.adk.workflow import Workflow, START
from google.adk import Agent
from google.adk.tools import google_search

# Step 1: Researcher (Uses Tools)
researcher = Agent(
    name="researcher",
    model="gemini-3.7-flash",
    instruction="Find 3 recent breakthroughs in the user provided topic using Google Search.",
    tools=[google_search]
)

# Step 2: Writer (Pure Reasoning)
writer = Agent(
    name="writer",
    model="gemini-3.7-flash",
    instruction="Summarize the provided research into a generic blog post format."
)

# Orchestrator using Graph-based Workflow
root_agent = Workflow(
    name="blog_pipeline",
    description="Researches and writes a blog post.",
    edges=[
        (START, researcher, writer)
    ]
)
# Note: The researcher's output automatically becomes the writer's input.
# The final output comes from the last agent in the sequence.
```

### **B. Parallel Workflow (The Fan-Out & Fan-In)**

*Pattern: Multiple agents work on the same input simultaneously, and a JoinNode waits for both outputs.*

**Scenario:** A "Code Review Board" where a **Security Analyst** and a **Performance Analyst** review code at the same time, and their outputs are aggregated by a `JoinNode` for a **Lead Engineer** to synthesize.

```python
from google.adk.workflow import Workflow, START, JoinNode
from google.adk import Agent

# Specialist 1
sec_analyst = Agent(
    name="sec_analyst",
    model="gemini-3.7-flash",
    instruction="Analyze the code strictly for security vulnerabilities (SQLi, XSS)."
)

# Specialist 2
perf_analyst = Agent(
    name="perf_analyst",
    model="gemini-3.7-flash",
    instruction="Analyze the code strictly for performance bottlenecks (O(n) complexity)."
)

# JoinNode to aggregate the parallel branches
join_node = JoinNode(name="join_node")

# Consolidator (Merges the parallel outputs)
lead_engineer = Agent(
    name="lead_engineer",
    model="gemini-3.7-flash",
    instruction="Synthesize the security and performance reports into a final verdict."
)

# Full System using Graph-based Workflow
root_agent = Workflow(
    name="code_review_system",
    description="Reviews code for security and performance.",
    edges=[
        (START, (sec_analyst, perf_analyst), join_node, lead_engineer)
    ]
)
# Note: JoinNode collects both reports and yields a dictionary containing:
# {'sec_analyst': sec_analyst_output, 'perf_analyst': perf_analyst_output}
```

### **C. Loop Workflow (The Iterative Refiner)**

*Pattern: Agents repeat until a condition is met, routed conditionally by setting ctx.route.*

**Scenario:** An **Iterative Content Refiner** where a **Writer** generates content, and a **Critic** evaluates it. If it needs work, the Critic routes it back to the Writer.

```python
from google.adk.workflow import Workflow, START
from google.adk import Agent
from google.adk.tools import ToolContext

# 1. Define a tool for the Critic to request revisions
def request_revision(ctx: ToolContext, feedback: str):
    """Call this function to request revisions and provide feedback to the writer."""
    ctx.route = "revise"
    return feedback

# 2. Writer generates content
writer = Agent(
    name="content_writer",
    model="gemini-3.7-flash",
    instruction="Write a technical blog post on the given topic."
)

# 3. Critic evaluates quality. If quality score is < 8/10, they request revision.
critic = Agent(
    name="content_critic",
    model="gemini-3.7-flash",
    instruction="""Review the content for quality.
    If the quality score is less than 8/10, call the 'request_revision' tool with your specific improvement feedback.
    If the quality score is 8/10 or higher, do not call any tools and output a confirmation.""",
    tools=[request_revision]
)

# 4. Loop using graph-based conditional edges
root_agent = Workflow(
    name="iterative_refiner",
    description="Iteratively refines content.",
    edges=[
        (START, writer, critic),
        (critic, {"revise": writer}) # Routes back to writer if ctx.route was set to "revise"
    ]
)
```

-----

### **D. Testing Your Agents**

You can test agents directly in Python:

```python
# At the end of agent.py or in a separate test file
if __name__ == "__main__":
    # Test the temperature converter agent
    response = root_agent.send_message("What is 100F in Celsius?")
    print(response)

    # Test with different queries
    response = root_agent.send_message("Convert 273.15K to Fahrenheit")
    print(response)
```

Alternatively, use the interactive CLI:
```bash
adk run my_first_agent
```

Or the web UI for a visual interface:
```bash
adk web
```

-----

### **E. Common Issues & Troubleshooting**

#### **Authentication Errors**
```
Error: Could not automatically determine credentials.
```
**Solution:** Run `gcloud auth application-default login` and ensure `GOOGLE_CLOUD_PROJECT` is set.

#### **Model Not Found**
```
Error: Model 'gemini-3.7-flash' not found
```
**Solution:** Verify the model is available in your region. Check `GOOGLE_CLOUD_LOCATION` is set to `global`.

#### **MCP Server Connection Issues**
```
Error: Failed to connect to MCP server
```
**Solution:**
1. Ensure Node.js and `npx` are installed: `node --version && npx --version`
2. Verify the workspace directory exists and has proper permissions
3. Check that the MCP package can be resolved: `npx -y @modelcontextprotocol/server-filesystem --help`

#### **Import Errors**
```
ImportError: cannot import name 'Agent' from 'google.adk.agents.llm_agent'
```
**Solution:**
1. Verify ADK installation: `pip show google-adk`
2. Ensure Python 3.10+: `python --version`
3. Reinstall if needed: `pip install --upgrade google-adk`

#### **Tool Not Being Called**
If the agent isn't using your custom tool:
1. Verify the function has a clear docstring
2. Make the instruction more explicit about when to use the tool
3. Test the tool function independently before adding to the agent

#### **Agent Not Found Error**
```
Error: No agent found. Make sure your agent.py defines 'root_agent'
```
**Solution:**
The ADK CLI commands (`adk run` and `adk web`) require your agent variable to be named exactly `root_agent`.

Update your agent.py to use:
```python
root_agent = Agent(...)  # ✓ Correct
```

Not:
```python
my_agent = Agent(...)  # ✗ Won't work with CLI
research_agent = Agent(...)  # ✗ Won't work with CLI
```

Note: This only applies to CLI usage. When calling agents programmatically in Python code, you can use any variable name.

-----

## 5. References & Next Steps

  * **ADK Documentation:** [https://google.github.io/adk-docs/](https://google.github.io/adk-docs/)
  * **Vertex AI Authentication:** [Google Cloud ADC Docs](https://cloud.google.com/docs/authentication/application-default-credentials)
  * **Model Context Protocol (MCP):** [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)

**Next Step:** Try running the **Parallel Workflow** example above by passing a snippet of Python code to the `code_review_system` agent to see how the two sub-agents critique it simultaneously.