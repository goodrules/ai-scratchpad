"""Shared instruction provider factory for runtime prompt style switching.

Provides make_instruction_provider() which creates an async callable
(InstructionProvider) that reads prompt_style from session state and
returns the appropriate prompt constant.
"""

from google.adk import Context
from google.adk.utils.instructions_utils import inject_session_state


def make_instruction_provider(retail_instruction: str, datacenter_instruction: str):
    """Create an async instruction provider that switches on prompt_style.

    Args:
        retail_instruction: The instruction template for retail mode.
        datacenter_instruction: The instruction template for datacenter mode.

    Returns:
        An async callable compatible with ADK's InstructionProvider protocol.
    """

    async def _provider(ctx: Context) -> str:
        style = ctx.state.get("prompt_style", "datacenter")
        template = retail_instruction if style == "retail" else datacenter_instruction
        return await inject_session_state(template, ctx)

    return _provider
