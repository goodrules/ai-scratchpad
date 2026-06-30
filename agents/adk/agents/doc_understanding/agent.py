import os
import mimetypes
from typing import Any
from google.adk import Agent, Context
from google.adk.tools import BaseTool
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from .config import MODEL_ID
from .prompt import SYSTEM_INSTRUCTION
from typing_extensions import override

class LoadFileTool(BaseTool):
    """A tool that loads a file and adds it to the LLM request contents."""

    def __init__(self):
        super().__init__(
            name='load_file',
            description=("""Loads a file from a local path into the session for this request.
NOTE: Call when you need access to a file (e.g., a document provide by the user)."""),
        )

    @override
    def _get_declaration(self) -> types.FunctionDeclaration | None:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'file_path': types.Schema(
                        type=types.Type.STRING,
                    ),
                },
                required=['file_path'],
            ),
        )

    @override
    async def run_async(
        self, *, args: dict[str, Any], tool_context: Context
    ) -> Any:
        file_path: str = args.get('file_path', '')
        if not os.path.exists(file_path):
             return {'error': f'File not found: {file_path}'}
        return {
            'file_path': file_path,
            'status': 'file_path validated. Content will be loaded.',
        }

    @override
    async def process_llm_request(
        self, *, tool_context: Context, llm_request: LlmRequest
    ) -> None:
        await super().process_llm_request(
            tool_context=tool_context,
            llm_request=llm_request,
        )
        
        if llm_request.contents and llm_request.contents[-1].parts:
            function_response = llm_request.contents[-1].parts[0].function_response
            if function_response and function_response.name == 'load_file':
                response = function_response.response or {}
                if 'error' in response:
                    return
                
                file_path = response.get('file_path', '')
                if file_path and os.path.exists(file_path):
                    try:
                         with open(file_path, 'rb') as f:
                             file_bytes = f.read()
                         
                         mime_type, _ = mimetypes.guess_type(file_path)
                         if not mime_type:
                              mime_type = 'application/octet-stream'
                         
                         part = types.Part(
                             inline_data=types.Blob(
                                 data=file_bytes,
                                 mime_type=mime_type
                             )
                         )
                         
                         llm_request.contents.append(
                             types.Content(
                                 role='user',
                                 parts=[part]
                             )
                         )
                    except Exception as e:
                         # Handle exception
                         pass

load_file_tool = LoadFileTool()

root_agent = Agent(
    model=MODEL_ID,
    name='document_understanding_agent',
    description='An agent for document understanding with hyper local citations.',
    instruction=SYSTEM_INSTRUCTION,
    tools=[load_file_tool],
)
