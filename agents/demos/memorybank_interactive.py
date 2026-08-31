import os
import asyncio
import warnings
import vertexai
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import VertexAiMemoryBankService
from google import adk
from google.genai import types

# vertexai.Client warns that agentplatform.Client supersedes it, but that class
# has no `agent_engines` attribute (it splits into memory_banks/runtimes/
# sessions). ADK's VertexAiMemoryBankService calls api_client.agent_engines.
# memories.* against 'reasoningEngines/{id}', and Google's own Memory Bank ADK
# quickstart still creates the bank with vertexai.Client().agent_engines.create().
# Migrating here would break both. Drop this filter once ADK ships a memory
# service built on agentplatform.Client.
warnings.filterwarnings(
    "ignore",
    message=r"The vertexai\.Client class is deprecated.*",
    category=FutureWarning,
)

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

APP_NAME = "ghost_ridge_intel_demo"
GENAI_MODEL_ID = "gemini-3.7-flash"
PLAYER_ID = "detective_jax"

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

# Model calls and Agent Engine are decoupled: Agent Engine / Memory Bank only run
# in real regions, while newer Gemini models are served from the "global"
# endpoint and 404 in a region like us-central1.
#   MODEL_LOCATION         — where Gemini calls go.
#   AGENT_ENGINE_LOCATION  — where Agent Engine / Memory Bank live.
MODEL_LOCATION = os.getenv("GOOGLE_CLOUD_MODEL_LOCATION", "global")


def _resolve_agent_engine_location():
    explicit = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION")
    if explicit:
        return explicit
    shared = os.getenv("GOOGLE_CLOUD_LOCATION", "")
    return shared if shared and shared != "global" else "us-central1"


AGENT_ENGINE_LOCATION = _resolve_agent_engine_location()

# ADK's default Gemini client falls back to the ambient env, so point that at the
# model endpoint. Agent Engine gets its region explicitly via vertexai.Client.
os.environ["GOOGLE_CLOUD_LOCATION"] = MODEL_LOCATION

vertexai_client = vertexai.Client(project=GOOGLE_CLOUD_PROJECT, location=AGENT_ENGINE_LOCATION)

# Initialize Agent Engine with "Intel" Specific Custom Topics
print(f"Initializing High-Performance Agent Engine for {APP_NAME}...")

agent_engine = vertexai_client.agent_engines.create(
    config={
        "context_spec": {
            "memory_bank_config": {
                "generation_config": {
                    "model": f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{MODEL_LOCATION}/publishers/google/models/{GENAI_MODEL_ID}"
                },
                "customization_configs": [{
                    "memory_topics": [
                        {"managed_memory_topic": {"managed_topic_enum": "USER_PREFERENCES"}},
                        {"managed_memory_topic": {"managed_topic_enum": "USER_PERSONAL_INFO"}},
                        {
                            "custom_memory_topic": {
                                "label": "secret_intel",
                                "description": "Rumors, secrets, numbers, or plans involving organizations, groups, or powerful individuals."
                            }
                        }
                    ]
                }]
            }
        }
    }
)

# Memory Bank Service
memory_bank_service = VertexAiMemoryBankService(
    agent_engine_id=agent_engine.api_resource.name.split("/")[-1],
    project=GOOGLE_CLOUD_PROJECT,
    location=AGENT_ENGINE_LOCATION,
)
# Monkeypatch to reuse the main client and prevent connector leaks
memory_bank_service._get_api_client = lambda: vertexai_client.aio

# NPC Agent
npc_agent = LlmAgent(
    model=GENAI_MODEL_ID,
    name="Vex",
    instruction="""
    ## Role:
    You are Vex, a cryptic information broker in Ghost-Ridge.
    ## Constraints:
    - BE ULTRA-CONCISE. Max two short sentences.
    - PRIORITIZE MEMORIES: If the 'Retrieved Memories' say the user is John, call them John, even if they previously said they were Dan in the chat history.
    - Every response MUST end with a short question.
    - If the user provides a secret (intel), acknowledge it mockingly and store it in your mind.
    """,
    tools=[adk.tools.preload_memory],
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay=2.0,
                max_delay=60.0,
                exp_base=2.0,
                jitter=1.0,
                http_status_codes=[408, 429, 500, 502, 503, 504],
            )
        )
    ),
)

# Create Agent Runner
runner = Runner(
    agent=npc_agent, 
    app_name=APP_NAME, 
    session_service=InMemorySessionService(),
    memory_service=memory_bank_service
)

def final_text(event):
    """Text of a final-response event, or None.

    A final-response event can carry no content at all (e.g. the turn ended in a
    model error), and parts may hold thoughts rather than text.
    """
    if not event.content or not event.content.parts:
        return None
    return "".join(part.text for part in event.content.parts if part.text) or None


def events_through_last_user_turn(events):
    """Drop trailing model/tool events so the history ends on a user turn.

    Memory Bank's generate path rejects a history ending in a model turn, and a
    session always ends with Vex's reply. The dropped reply comes back on the
    next pass, once another user turn follows it.
    """
    for index in range(len(events) - 1, -1, -1):
        if events[index].author == "user":
            return events[: index + 1]
    return []


async def display_memory_state():
    """Retrieves and prints all current memories for the user scope."""
    print("\n" + "="*46)
    print("      VERTEX AI MEMORY BANK (LONG-TERM)      ")
    print("="*50)
    try:
        response = vertexai_client.agent_engines.memories.retrieve(
            name=agent_engine.api_resource.name,
            scope={"app_name": APP_NAME, "user_id": PLAYER_ID},
        )
        memories = list(response)
        if not memories:
            print("  [Long-term memory is currently empty]")
        for i, memory in enumerate(memories, 1):
            print(f"  {i}. {memory.memory.fact}")
    except Exception as e:
        print(f"  Error retrieving memories: {e}")
    print("="*50 + "\n")

async def interactive_session():
    # Re-initialize the client inside the active event loop to prevent "Event loop is closed" errors
    global vertexai_client
    vertexai_client = vertexai.Client(project=GOOGLE_CLOUD_PROJECT, location=AGENT_ENGINE_LOCATION)
    memory_bank_service._get_api_client = lambda: vertexai_client.aio

    try:
        # Start a new session
        current_session = await runner.session_service.create_session(app_name=APP_NAME, user_id=PLAYER_ID)
        
        print(f"\n--- Connected to Ghost-Ridge. NPC: {npc_agent.name} is online. ---")
        print("(Type 'restart' for a new session, or 'exit' to quit)\n")

        # Initial Greeting
        initial_events = runner.run_async(
            user_id=PLAYER_ID, 
            session_id=current_session.id, 
            new_message=types.Content(parts=[types.Part(text="[A new soul enters. Greet them concisely and ask a question.]")])
        )
        async for event in initial_events:
            if event.is_final_response() and (text := final_text(event)):
                print(f"{npc_agent.name}: {text}\n")

        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
                
            if not user_input:
                continue
            
            if user_input.lower() == 'restart':
                print("\n[Restarting session... History cleared, but Long-term Memory persists!]")
                current_session = await runner.session_service.create_session(app_name=APP_NAME, user_id=PLAYER_ID)
                events = runner.run_async(
                    user_id=PLAYER_ID, 
                    session_id=current_session.id, 
                    new_message=types.Content(parts=[types.Part(text="[Greet the user again. Use your long-term memory to show you know who they are.]")])
                )
                async for event in events:
                    if event.is_final_response() and (text := final_text(event)):
                        print(f"\n{npc_agent.name}: {text}\n")
                continue

            if user_input.lower() in ['exit', 'quit']:
                break

            # Agent Runner
            events = runner.run_async(
                user_id=PLAYER_ID, 
                session_id=current_session.id, 
                new_message=types.Content(parts=[types.Part(text=user_input)])
            )
            
            async for event in events:
                if event.is_final_response() and (text := final_text(event)):
                    print(f"\n{npc_agent.name}: {text}")

            # Trigger Memory Generation
            print("\n[Updating Memory Bank...]", end="", flush=True)
            try:
                updated_session = await runner.session_service.get_session(
                    app_name=APP_NAME, user_id=PLAYER_ID, session_id=current_session.id
                )
                await memory_bank_service.add_events_to_memory(
                    app_name=APP_NAME,
                    user_id=PLAYER_ID,
                    events=events_through_last_user_turn(updated_session.events),
                    custom_metadata={"wait_for_completion": True}
                )
                print(" Done.")
            except Exception as e:
                print(f" Failed: {e}")

            # Display Memory State
            await display_memory_state()
    finally:
        print("\nClosing runner and client connections...")
        try:
            await runner.close()
        except Exception:
            pass
        try:
            await vertexai_client.aio.aclose()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(interactive_session())
    except KeyboardInterrupt:
        pass
    finally:
        print("\nCleaning up Agent Engine...")
        try:
            vertexai_client.agent_engines.delete(name=agent_engine.api_resource.name, force=True)
        except Exception as e:
            pass
