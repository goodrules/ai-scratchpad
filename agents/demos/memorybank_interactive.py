import os
import asyncio
import vertexai
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import VertexAiMemoryBankService
from google import adk
from google.genai import types

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

APP_NAME = "ghost_ridge_intel_demo"
GENAI_MODEL_ID = "gemini-2.5-pro"
PLAYER_ID = "detective_jax"

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")

vertexai_client = vertexai.Client(project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)

# Initialize Agent Engine with "Intel" Specific Custom Topics
print(f"Initializing High-Performance Agent Engine for {APP_NAME}...")

agent_engine = vertexai_client.agent_engines.create(
    config={
        "context_spec": {
            "memory_bank_config": {
                "generation_config": {
                    "model": f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/publishers/google/models/{GENAI_MODEL_ID}"
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
    location=GOOGLE_CLOUD_LOCATION,
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
    tools=[adk.tools.preload_memory]
)

# Create Agent Runner
runner = Runner(
    agent=npc_agent, 
    app_name=APP_NAME, 
    session_service=InMemorySessionService(),
    memory_service=memory_bank_service
)

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
    vertexai_client = vertexai.Client(project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
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
            if event.is_final_response():
                print(f"{npc_agent.name}: {event.content.parts[0].text}\n")

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
                    if event.is_final_response():
                        print(f"\n{npc_agent.name}: {event.content.parts[0].text}\n")
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
                if event.is_final_response():
                    print(f"\n{npc_agent.name}: {event.content.parts[0].text}")

            # Trigger Memory Generation
            print("\n[Updating Memory Bank...]", end="", flush=True)
            try:
                updated_session = await runner.session_service.get_session(
                    app_name=APP_NAME, user_id=PLAYER_ID, session_id=current_session.id
                )
                await memory_bank_service.add_events_to_memory(
                    app_name=APP_NAME,
                    user_id=PLAYER_ID,
                    events=updated_session.events,
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
