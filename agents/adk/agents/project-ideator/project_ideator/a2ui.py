"""A2UI Protocol Payload Generators and Builders for Project Ideator.

Generates declarative JSON messages adhering to the A2UI v0.8 specification
compatible with Gemini Enterprise and the standard v0.8 catalog:
- beginRendering
- surfaceUpdate
- dataModelUpdate
"""

from __future__ import annotations

from typing import Any

from .config import A2UI_CATALOG_ID, A2UI_MIME_TYPE, A2UI_VERSION, MAIN_SURFACE_ID
from .models import GrillStage


def build_a2ui_envelope(
    begin_rendering: dict[str, Any] | None = None,
    surface_update: dict[str, Any] | None = None,
    data_model_update: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build a sequence of A2UI v0.8 protocol messages for Gemini Enterprise and A2A."""
    messages = []
    if begin_rendering:
        messages.append({
            "beginRendering": begin_rendering,
        })
    if surface_update:
        messages.append({
            "surfaceUpdate": surface_update,
        })
    if data_model_update:
        messages.append({
            "dataModelUpdate": data_model_update,
        })
    return messages



def generate_stage_a2ui_payload(
    stage: GrillStage,
    question_text: str,
    options: list[str],
    current_summary: str = "",
    freeform_placeholder: str = "Add your custom answer or additional context...",
    surface_id: str = MAIN_SURFACE_ID,
) -> dict[str, Any]:
    """Generate complete A2UI JSON payload for a grilling interview stage adhering to v0.8 spec."""
    total_stages = 5
    current_num = stage.stage_number

    # Components list in v0.8 format
    components: list[dict[str, Any]] = [
        {
            "id": "progress_tracker",
            "component": {
                "Text": {
                    "text": {
                        "literalString": f"Stage {current_num} of {total_stages}: {stage.display_title}"
                    },
                    "usageHint": "caption",
                }
            },
        },
        {
            "id": "question_heading",
            "component": {
                "Text": {
                    "text": {"literalString": question_text},
                    "usageHint": "h2",
                }
            },
        },
    ]

    root_children: list[str] = ["progress_tracker", "question_heading"]

    if current_summary:
        components.extend([
            {
                "id": "context_card_header",
                "component": {
                    "Text": {
                        "text": {"literalString": "Current Project Context:"},
                        "usageHint": "caption",
                    }
                },
            },
            {
                "id": "context_card_body",
                "component": {
                    "Text": {
                        "text": {"literalString": current_summary},
                        "usageHint": "body",
                    }
                },
            },
        ])
        root_children.extend(["context_card_header", "context_card_body"])

    # Add option choice buttons
    components.append({
        "id": "options_instruction",
        "component": {
            "Text": {
                "text": {
                    "literalString": (
                        "Select a recommended direction or provide custom input"
                        " below:"
                    )
                },
                "usageHint": "body",
            }
        },
    })
    root_children.append("options_instruction")

    for idx, opt in enumerate(options):
        btn_text_id = f"opt_text_{idx}"
        btn_id = f"opt_btn_{idx}"
        root_children.append(btn_id)
        is_recommended = "(Recommended)" in opt or idx == 0

        components.append({
            "id": btn_text_id,
            "component": {
                "Text": {
                    "text": {"literalString": opt},
                    "usageHint": "body",
                }
            },
        })
        components.append({
            "id": btn_id,
            "component": {
                "Button": {
                    "child": btn_text_id,
                    "primary": is_recommended,
                    "action": {
                        "name": "select_stage_option",
                        "context": [
                            {
                                "key": "stage",
                                "value": {"literalString": stage.value},
                            },
                            {
                                "key": "selected_option",
                                "value": {"literalString": opt},
                            },
                            {
                                "key": "option_index",
                                "value": {"literalNumber": idx},
                            },
                        ],
                    },
                }
            },
        })

    # Add freeform conversational guidance hint (TextField is not supported in production Gemini Enterprise)
    root_children.append("freeform_hint")
    components.append({
        "id": "freeform_hint",
        "component": {
            "Text": {
                "text": {
                    "literalString": (
                        "💡 To choose a direction, click a button above. To customize or add nuances, simply type in the chat."
                    )
                },
                "usageHint": "caption",
            }
        },
    })

    # Insert root Card and Column containers adhering to Gemini Enterprise <ucs-a2ui> requirements
    components.insert(
        0,
        {
            "id": "root-card",
            "component": {
                "Card": {
                    "child": "root-column",
                }
            },
        },
    )
    components.insert(
        1,
        {
            "id": "root-column",
            "component": {
                "Column": {
                    "children": {"explicitList": root_children},
                    "alignment": "stretch",
                    "distribution": "start",
                }
            },
        },
    )

    messages = build_a2ui_envelope(
        begin_rendering={
            "surfaceId": surface_id,
            "root": "root-card",
        },
        surface_update={
            "surfaceId": surface_id,
            "components": components,
        },
    )

    return {
        "mime_type": A2UI_MIME_TYPE,
        "surface_id": surface_id,
        "stage": stage.value,
        "a2ui_messages": messages,
    }


def generate_prd_review_a2ui_payload(
    prd_markdown: str,
    project_title: str,
    filename: str = "PRD.md",
    surface_id: str = MAIN_SURFACE_ID,
) -> dict[str, Any]:
    """Generate A2UI payload for the final PRD review and download stage."""
    components = [
        {
            "id": "prd_header",
            "component": {
                "Text": {
                    "text": {
                        "literalString": (
                            f"Stage 5 of 5: Final PRD for {project_title}"
                        )
                    },
                    "usageHint": "h1",
                }
            },
        },
        {
            "id": "prd_instructions",
            "component": {
                "Text": {
                    "text": {
                        "literalString": (
                            "Review your generated Product Requirements"
                            " Document below. Click 'Export & Save PRD.md' to"
                            " generate your downloadable file."
                        )
                    },
                    "usageHint": "body",
                }
            },
        },
        {
            "id": "prd_content_view",
            "component": {
                "Text": {
                    "text": {"literalString": prd_markdown},
                    "usageHint": "body",
                }
            },
        },
        {
            "id": "btn_export_text",
            "component": {
                "Text": {
                    "text": {"literalString": f"📥 Export & Save {filename}"},
                    "usageHint": "body",
                }
            },
        },
        {
            "id": "btn_export",
            "component": {
                "Button": {
                    "child": "btn_export_text",
                    "primary": True,
                    "action": {
                        "name": "export_prd_file",
                        "context": [
                            {
                                "key": "filename",
                                "value": {"literalString": filename},
                            },
                            {
                                "key": "action",
                                "value": {"literalString": "download"},
                            },
                        ],
                    },
                }
            },
        },
        {
            "id": "btn_revise_text",
            "component": {
                "Text": {
                    "text": {"literalString": "🔄 Revise Requirements"},
                    "usageHint": "body",
                }
            },
        },
        {
            "id": "btn_revise",
            "component": {
                "Button": {
                    "child": "btn_revise_text",
                    "primary": False,
                    "action": {
                        "name": "revise_stage",
                        "context": [
                            {
                                "key": "stage",
                                "value": {
                                    "literalString": (
                                        GrillStage.PROBLEM_AND_GOAL.value
                                    )
                                },
                            },
                        ],
                    },
                }
            },
        },
    ]

    components.insert(
        0,
        {
            "id": "root-card",
            "component": {
                "Card": {
                    "child": "root-column",
                }
            },
        },
    )
    components.insert(
        1,
        {
            "id": "root-column",
            "component": {
                "Column": {
                    "children": {
                        "explicitList": [
                            "prd_header",
                            "prd_instructions",
                            "prd_content_view",
                            "btn_export",
                            "btn_revise",
                        ]
                    },
                    "alignment": "stretch",
                    "distribution": "start",
                }
            },
        },
    )

    messages = build_a2ui_envelope(
        begin_rendering={
            "surfaceId": surface_id,
            "root": "root-card",
        },
        surface_update={
            "surfaceId": surface_id,
            "components": components,
        },
    )

    return {
        "mime_type": A2UI_MIME_TYPE,
        "surface_id": surface_id,
        "a2ui_messages": messages,
    }


def generate_export_success_a2ui_payload(
    file_path: str,
    project_title: str,
    surface_id: str = MAIN_SURFACE_ID,
) -> dict[str, Any]:
    """Generate A2UI payload indicating successful file export with open/download actions."""
    components = [
        {
            "id": "success_title",
            "component": {
                "Text": {
                    "text": {
                        "literalString": "✅ PRD Successfully Exported!"
                    },
                    "usageHint": "h2",
                }
            },
        },
        {
            "id": "success_body",
            "component": {
                "Text": {
                    "text": {
                        "literalString": (
                            "Your Product Requirements Document for"
                            f" '{project_title}' has been generated and saved"
                            f" locally to: `{file_path}`."
                        )
                    },
                    "usageHint": "body",
                }
            },
        },
        {
            "id": "action_finish_text",
            "component": {
                "Text": {
                    "text": {
                        "literalString": "Start Next Project Ideation"
                    },
                    "usageHint": "body",
                }
            },
        },
        {
            "id": "action_finish_btn",
            "component": {
                "Button": {
                    "child": "action_finish_text",
                    "primary": True,
                    "action": {
                        "name": "reset_session",
                        "context": [],
                    },
                }
            },
        },
    ]

    components.insert(
        0,
        {
            "id": "root-card",
            "component": {
                "Card": {
                    "child": "root-column",
                }
            },
        },
    )
    components.insert(
        1,
        {
            "id": "root-column",
            "component": {
                "Column": {
                    "children": {
                        "explicitList": [
                            "success_title",
                            "success_body",
                            "action_finish_btn",
                        ]
                    },
                    "alignment": "stretch",
                    "distribution": "start",
                }
            },
        },
    )

    messages = build_a2ui_envelope(
        begin_rendering={
            "surfaceId": surface_id,
            "root": "root-card",
        },
        surface_update={
            "surfaceId": surface_id,
            "components": components,
        },
    )

    return {
        "mime_type": A2UI_MIME_TYPE,
        "surface_id": surface_id,
        "a2ui_messages": messages,
    }

