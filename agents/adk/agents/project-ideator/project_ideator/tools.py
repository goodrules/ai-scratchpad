"""Tool implementations for Project Ideator Agent.

Provides callable ADK tools to render interactive A2UI surfaces,
manage stage transitions, construct PRDs, and export downloadable files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .a2ui import (
    generate_export_success_a2ui_payload,
    generate_prd_review_a2ui_payload,
    generate_stage_a2ui_payload,
)
from .config import DEFAULT_PRD_FILENAME
from .models import GrillStage, PRDSpec


def get_ideation_stages() -> dict[str, Any]:
    """Retrieve the sequence of 5 grilling interview stages and their descriptions."""
    stages = [
        {
            "stage_number": s.stage_number,
            "stage_name": s.value,
            "display_title": s.display_title,
        }
        for s in GrillStage
    ]
    return {
        "status": "success",
        "total_stages": len(stages),
        "stages": stages,
    }


def render_ideation_stage(
    stage: str,
    question_text: str,
    options: list[str],
    current_summary: str = "",
    freeform_placeholder: str = "Add your custom thoughts or nuances here...",
) -> dict[str, Any]:
    """Render an interactive A2UI surface for a grilling interview stage.

    Args:
        stage: The current grilling stage name ('problem_and_goal', 'target_audience',
               'pain_and_alternatives', 'scope_and_non_goals', or 'prd_draft').
        question_text: The sharp, probing question to present to the user.
        options: 2 to 4 recommended multiple-choice options for the user to click.
        current_summary: Concise running summary of agreed points so far.
        freeform_placeholder: Placeholder text for the optional custom input box.

    Returns:
        A dictionary with status, stage info, and standard A2UI messages for UI clients.
    """
    try:
        grill_stage = GrillStage(stage)
    except ValueError:
        # Fallback if an informal stage string is passed
        grill_stage = GrillStage.PROBLEM_AND_GOAL

    payload = generate_stage_a2ui_payload(
        stage=grill_stage,
        question_text=question_text,
        options=options,
        current_summary=current_summary,
        freeform_placeholder=freeform_placeholder,
    )

    a2ui_tag = f"<a2ui-json>{json.dumps(payload['a2ui_messages'])}</a2ui-json>"

    return {
        "status": "success",
        "stage": grill_stage.value,
        "stage_title": grill_stage.display_title,
        "stage_number": grill_stage.stage_number,
        "a2ui_payload": payload,
        "a2ui_tag": a2ui_tag,
        "instructions_to_agent": (
            f"Rendered interactive A2UI surface for {grill_stage.display_title}. "
            "Provide 1-2 brief sentences of conversational framing or guidance in your response (e.g. inviting the user to choose an option below or share their concept). "
            "Do NOT print numbered options or questionnaire lists in text, and do NOT include raw <a2ui-json> or JSON tags in your response."
        ),
    }


def render_prd_preview(
    project_title: str,
    tagline: str,
    target_persona: str,
    problem_statement: str,
    pain_points: list[str],
    core_features: list[str],
    non_goals: list[str],
    success_metrics: list[str],
    riskiest_assumption: str = "",
    first_slice_milestone: str = "",
    tech_stack_notes: list[str] | None = None,
    filename: str = DEFAULT_PRD_FILENAME,
) -> dict[str, Any]:
    """Assemble a comprehensive PRD specification and render an A2UI review surface.

    Args:
        project_title: Name of the project.
        tagline: 1-sentence commitment: what, for whom, why now.
        target_persona: The specific user role experiencing this problem.
        problem_statement: Clear description of the problem today.
        pain_points: List of current frictions/workarounds.
        core_features: Functional requirements for the first slice (V1).
        non_goals: Explicitly cut / out of scope items.
        success_metrics: Observable definitions of done.
        riskiest_assumption: The fatal assumption to test first.
        first_slice_milestone: What should be working by the end of week 1.
        tech_stack_notes: Optional architecture recommendations.
        filename: Target filename for download (defaults to PRD.md).

    Returns:
        Structured PRD markdown and A2UI review surface payload.
    """
    spec = PRDSpec(
        title=project_title,
        tagline=tagline,
        target_persona=target_persona,
        problem_statement=problem_statement,
        pain_points=pain_points,
        core_features=core_features,
        non_goals=non_goals,
        success_metrics=success_metrics,
        riskiest_assumption=riskiest_assumption,
        first_slice_milestone=first_slice_milestone,
        tech_stack_notes=tech_stack_notes or [],
    )

    prd_md = spec.to_markdown()
    payload = generate_prd_review_a2ui_payload(
        prd_markdown=prd_md,
        project_title=project_title,
        filename=filename,
    )
    a2ui_tag = f"<a2ui-json>{json.dumps(payload['a2ui_messages'])}</a2ui-json>"

    return {
        "status": "success",
        "project_title": project_title,
        "prd_markdown": prd_md,
        "a2ui_payload": payload,
        "a2ui_tag": a2ui_tag,
        "message": "PRD review surface generated. Ready for user export.",
    }


def export_prd(
    project_title: str,
    prd_markdown: str,
    filename: str = DEFAULT_PRD_FILENAME,
    target_directory: str = "",
) -> dict[str, Any]:
    """Save the final PRD markdown to disk and return download confirmation with A2UI surface.

    Args:
        project_title: Project name.
        prd_markdown: The complete markdown content of the PRD.
        filename: Output filename (e.g., 'PRD.md' or 'MY_PROJECT_PRD.md').
        target_directory: Target directory to save file in. Defaults to current directory.

    Returns:
        Export status, saved file path, file size, and A2UI confirmation payload.
    """
    if not target_directory:
        # Default to the agent directory or current working directory
        target_dir = Path.cwd()
    else:
        target_dir = Path(target_directory)

    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / filename

    try:
        file_path.write_text(prd_markdown, encoding="utf-8")
        file_size = file_path.stat().st_size
        abs_path = str(file_path.resolve())

        success_payload = generate_export_success_a2ui_payload(
            file_path=abs_path,
            project_title=project_title,
        )
        a2ui_tag = f"<a2ui-json>{json.dumps(success_payload['a2ui_messages'])}</a2ui-json>"

        return {
            "status": "success",
            "message": f"Successfully exported PRD to {abs_path}",
            "file_path": abs_path,
            "size_bytes": file_size,
            "file_size_bytes": file_size,
            "filename": filename,
            "a2ui_payload": success_payload,
            "a2ui_tag": a2ui_tag,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to write PRD file: {e}",
            "file_path": str(file_path),
        }
