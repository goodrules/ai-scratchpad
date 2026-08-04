from google.adk import Agent, Context

# --- Tool Definition ---
def exit_loop(tool_context: Context):
  """Call this function ONLY when the critique is 'APPROVED', indicating the story is finished and no more changes are needed."""
  print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
  tool_context.state["loop_exited"] = True
  # Return empty dict as tools should typically return JSON-serializable output
  return {"status": "approved", "message": "Story approved. Exiting refinement loop."}

# This agent refines the story based on critique OR calls the exit_loop function.
refiner_agent = Agent(
    name="RefinerAgent",
    model="gemini-3.5-flash",
    instruction="""You are a skilled story refiner who transforms good drafts into excellent stories. You have a story draft and editorial feedback to work with.

    Story Draft: {current_story}
    Critique: {critique}

    **Your Task:**
    - IF the critique is EXACTLY "APPROVED", you MUST call the `exit_loop` function and do nothing else.
    - OTHERWISE, thoughtfully revise the story to address the critique while preserving what works well.

    **Refinement Guidelines:**
    - Identify and preserve the story's core strengths (compelling characters, vivid scenes, effective moments)
    - Address each point in the critique with targeted, meaningful changes
    - Maintain consistency in worldbuilding details, character voices, and narrative tone
    - Ensure revisions enhance the overall story rather than just patch issues
    - Keep the story within 750-1000 words

    Output the complete revised story with no title, introduction, or meta-commentary.""",
    
    output_key="current_story", # It overwrites the story with the new, refined version.
    tools=[exit_loop], # The tool is now correctly initialized with the function reference.
)