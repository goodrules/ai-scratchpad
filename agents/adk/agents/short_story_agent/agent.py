from google.adk import Workflow, Context
from google.adk.workflow import START, node

from .subagents import (
    editor_agent,
    refiner_agent,
    writer_agent,
    planner_agent
)

@node(rerun_on_resume=True)
async def refiner_node(ctx: Context):
    # Initialize refinement counter in context state if not present
    if "refine_count" not in ctx.state:
        ctx.state["refine_count"] = 0

    if "loop_exited" not in ctx.state:
        ctx.state["loop_exited"] = False

    # Save the current story in case the agent exits and overwrites it
    original_story = ctx.state.get("current_story", "")

    # Run the refiner agent
    await ctx.run_node(refiner_agent)

    # If the loop exited, restore the original story to prevent agent meta-commentary from overwriting it
    if ctx.state.get("loop_exited"):
        ctx.state["current_story"] = original_story

    ctx.state["refine_count"] += 1

    # Check if loop exited or max iterations (3) reached
    if ctx.state.get("loop_exited") or ctx.state["refine_count"] >= 3:
        ctx.route = "exit"
    else:
        ctx.route = "continue"

@node
async def approved_story_node(ctx: Context) -> str:
    # Return the final story from the state
    return ctx.state.get("current_story", "")

# The root agent is a Workflow that defines the overall graph: Initial Write -> Refinement Loop.
root_agent = Workflow(
    name="StoryPipeline",
    edges=[
        (START, planner_agent, writer_agent, editor_agent, refiner_node),
        (refiner_node, {"continue": editor_agent, "exit": approved_story_node}),
    ],
)