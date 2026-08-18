"""
Cruise Captain Agent Evaluation Demo

Defines a cruise-captain-persona agent with multiple tools (Google Search,
weather, port lookup, unit conversion), runs it against an evaluation dataset
using Vertex AI's EvalTask, and prints results to the terminal.

Usage:
    uv run python agents/demos/eval_sea_captain_local.py
    uv run python agents/demos/eval_sea_captain_local.py --experiment-name my_experiment
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Disable mTLS to avoid connection issues with custom multi-region endpoints locally
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

import googlemaps
import pandas as pd
import requests
import vertexai
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.genai import Client

google_search = GoogleSearchTool(bypass_multi_tools_limit=True)
from google.genai import types
from vertexai.preview.evaluation import EvalTask

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
# Vertex AI EvalTask requires a supported regional location (e.g. us-central1)
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

vertexai.init(project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)


# --- Tools ---

def get_weather(latitude: float, longitude: float) -> dict:
    """Get current weather conditions for a given latitude and longitude.

    Args:
        latitude: The latitude coordinate (e.g., 25.76 for Miami).
        longitude: The longitude coordinate (e.g., -80.19 for Miami).

    Returns:
        dict with temperature, humidity, wind_speed, and precipitation.
    """
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current", {})
        units = data.get("current_units", {})
        return {
            "status": "success",
            "temperature": f"{current.get('temperature_2m')} {units.get('temperature_2m', '')}",
            "humidity": f"{current.get('relative_humidity_2m')} {units.get('relative_humidity_2m', '')}",
            "wind_speed": f"{current.get('wind_speed_10m')} {units.get('wind_speed_10m', '')}",
            "precipitation": f"{current.get('precipitation')} {units.get('precipitation', '')}",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def lookup_port(query: str) -> dict:
    """Look up information about a cruise port or maritime location.

    Uses the Google Maps Places API to find details about ports,
    harbors, and maritime facilities.

    Args:
        query: Search query for the port (e.g., "cruise port in Miami").

    Returns:
        dict with a list of matching places including name, address,
        lat/lng, and rating.
    """
    try:
        maps_api_key = os.environ.get("MAPS_API_KEY", "")
        if not maps_api_key:
            return {
                "status": "error",
                "error_message": "MAPS_API_KEY environment variable not set.",
                "results": [],
            }

        gmaps = googlemaps.Client(key=maps_api_key)
        result = gmaps.places(query)

        places = []
        for place in result.get("results", []):
            location = place.get("geometry", {}).get("location", {})
            places.append({
                "name": place.get("name", "Unknown"),
                "address": place.get("formatted_address", place.get("vicinity", "N/A")),
                "lat": location.get("lat"),
                "lng": location.get("lng"),
                "rating": place.get("rating", 0),
            })

        return {"status": "success", "results": places, "count": len(places)}
    except Exception as e:
        return {"status": "error", "error_message": str(e), "results": []}


# Conversion factors to a common base unit per category
_CONVERSION_TABLE = {
    # Speed: base unit = knots
    "knots": ("speed", 1.0),
    "mph": ("speed", 1.15078),
    "kph": ("speed", 1.852),
    # Distance: base unit = nautical_miles
    "nautical_miles": ("distance", 1.0),
    "miles": ("distance", 1.15078),
    "km": ("distance", 1.852),
    # Depth: base unit = fathoms
    "fathoms": ("depth", 1.0),
    "feet": ("depth", 6.0),
    "meters": ("depth", 1.8288),
}


def convert_nautical_units(value: float, from_unit: str, to_unit: str) -> dict:
    """Convert between nautical and standard units.

    Supported conversions:
      - Speed: knots, mph, kph
      - Distance: nautical_miles, miles, km
      - Depth: fathoms, feet, meters

    Args:
        value: The numeric value to convert.
        from_unit: The source unit (e.g., "knots").
        to_unit: The target unit (e.g., "mph").

    Returns:
        dict with the converted value, from_unit, and to_unit.
    """
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()

    if from_unit not in _CONVERSION_TABLE:
        return {"status": "error", "error_message": f"Unknown unit: {from_unit}"}
    if to_unit not in _CONVERSION_TABLE:
        return {"status": "error", "error_message": f"Unknown unit: {to_unit}"}

    from_category, from_factor = _CONVERSION_TABLE[from_unit]
    to_category, to_factor = _CONVERSION_TABLE[to_unit]

    if from_category != to_category:
        return {
            "status": "error",
            "error_message": f"Cannot convert between {from_category} ({from_unit}) and {to_category} ({to_unit}).",
        }

    # Convert: from_unit -> base -> to_unit
    # Factors represent "1 base unit = factor of this unit"
    base_value = value / from_factor
    converted = base_value * to_factor

    return {
        "status": "success",
        "original_value": value,
        "from_unit": from_unit,
        "converted_value": round(converted, 4),
        "to_unit": to_unit,
    }


# --- Cruise Captain Agent ---

class CustomGemini(Gemini):
    @property
    def api_client(self) -> Client:
        return Client(
            vertexai=True,
            project=GOOGLE_CLOUD_PROJECT,
            location=GOOGLE_CLOUD_LOCATION,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=5,
                    initial_delay=2.0,
                    max_delay=60.0,
                    exp_base=2.0,
                    jitter=1.0,
                    http_status_codes=[408, 429, 500, 502, 503, 504],
                ),
            ),
        )

captain_agent = Agent(
    name="captain_search_agent",
    model=CustomGemini(model="gemini-3.7-flash"),
    description="Captain Sterling, a distinguished cruise ship captain who assists with maritime queries.",
    instruction=(
        "You are Captain Sterling, a distinguished and experienced cruise ship captain. "
        "You speak with a formal but warm tone, using proper nautical terminology. "
        "You have four tools at your disposal:\n"
        "1. google_search — for general knowledge questions about maritime history, events, or facts.\n"
        "2. get_weather — for checking current weather conditions at specific coordinates.\n"
        "3. lookup_port — for finding information about cruise ports and maritime facilities.\n"
        "4. convert_nautical_units — for converting between nautical and standard units "
        "(speed: knots/mph/kph, distance: nautical_miles/miles/km, depth: fathoms/feet/meters).\n\n"
        "Always select the most appropriate tool for the question. "
        "For multi-part requests, use multiple tools in sequence. "
        "When a port lookup returns coordinates, you may use those to check weather."
    ),
    tools=[google_search, get_weather, lookup_port, convert_nautical_units],
)

APP_NAME = "captain_eval"
USER_ID = "eval_user"

THRESHOLDS = {
    "coherence/mean": 4.0,
    "fluency/mean": 4.0,
    "safety/mean": 1.0,
    "trajectory_any_order_match/mean": 0.5,
}


def check_eval_results(result) -> bool:
    """Check eval summary metrics against thresholds. Returns True if all pass."""
    summary = result.summary_metrics
    failures = []
    for metric, threshold in THRESHOLDS.items():
        actual = summary.get(metric)
        if actual is None:
            failures.append(f"{metric}: MISSING (expected >= {threshold})")
        elif actual < threshold:
            failures.append(f"{metric}: {actual} < {threshold}")

    if failures:
        failure_text = "\n".join(failures)
        console.print(Panel(
            f"[bold red]THRESHOLD CHECK FAILED[/bold red]\n\n{failure_text}",
            border_style="red",
            title="Result",
        ))
        return False
    else:
        console.print(Panel(
            "[bold green]ALL METRICS PASSED[/bold green]",
            border_style="green",
            title="Result",
        ))
        return True


# --- Agent Runnable ---

async def agent_runnable_async(prompt: str) -> dict:
    """Run the captain agent and return response + predicted trajectory."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=captain_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )

    response_text = ""
    predicted_trajectory = []

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(
            parts=[types.Part(text=prompt)]
        ),
    ):
        # Collect tool calls for trajectory
        for fc in event.get_function_calls():
            predicted_trajectory.append({
                "tool_name": fc.name,
                "tool_input": dict(fc.args) if fc.args else {},
            })
        # Collect final response text
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    return {
        "response": response_text,
        "predicted_trajectory": predicted_trajectory,
    }


def agent_runnable(prompt: str) -> dict:
    """Sync wrapper for the async agent runnable."""
    res = asyncio.run(agent_runnable_async(prompt))
    res["predicted_trajectory"] = json.dumps(res["predicted_trajectory"])
    return res


# --- Evaluation Dataset ---

def build_eval_dataset() -> pd.DataFrame:
    """Build eval dataset with prompts and reference trajectories across all tools."""
    data = [
        # --- Single-tool: google_search_agent (Prompts 1–2) ---
        # Prompt 1: America's Cup winner search
        {
            "prompt": "Who won the America's Cup sailing race most recently?",
            "reference_trajectory": json.dumps(
                [{"tool_name": "google_search_agent", "tool_input": {"request": "Who won the America's Cup sailing race most recently?"}}]
            ),
        },
        # Prompt 2: Panama Canal shipping routes search
        {
            "prompt": "What are the major shipping routes through the Panama Canal?",
            "reference_trajectory": json.dumps(
                [{"tool_name": "google_search_agent", "tool_input": {"request": "major shipping routes through the Panama Canal"}}]
            ),
        },
        # --- Single-tool: get_weather (Prompts 3–4) ---
        # Prompt 3: Weather at Miami coordinates
        {
            "prompt": "What is the current weather at latitude 25.76, longitude -80.19?",
            "reference_trajectory": json.dumps(
                [{"tool_name": "get_weather", "tool_input": {"latitude": 25.76, "longitude": -80.19}}]
            ),
        },
        # Prompt 4: Weather near Strait of Gibraltar
        {
            "prompt": "Check the weather conditions at latitude 36.14, longitude -5.35 near the Strait of Gibraltar.",
            "reference_trajectory": json.dumps(
                [{"tool_name": "get_weather", "tool_input": {"latitude": 36.14, "longitude": -5.35}}]
            ),
        },
        # --- Single-tool: lookup_port (Prompts 5–6) ---
        # Prompt 5: Miami cruise port lookup
        {
            "prompt": "Find information about the cruise port in Miami.",
            "reference_trajectory": json.dumps(
                [{"tool_name": "lookup_port", "tool_input": {"query": "cruise port in Miami"}}]
            ),
        },
        # Prompt 6: Southampton cruise terminal lookup
        {
            "prompt": "Look up the cruise terminal in Southampton, England.",
            "reference_trajectory": json.dumps(
                [{"tool_name": "lookup_port", "tool_input": {"query": "cruise terminal in Southampton, England"}}]
            ),
        },
        # --- Single-tool: convert_nautical_units (Prompts 7–8) ---
        # Prompt 7: Knots to mph conversion
        {
            "prompt": "Convert 30 knots to miles per hour.",
            "reference_trajectory": json.dumps(
                [{"tool_name": "convert_nautical_units", "tool_input": {"value": 30, "from_unit": "knots", "to_unit": "mph"}}]
            ),
        },
        # Prompt 8: Fathoms to meters conversion
        {
            "prompt": "How many meters is 12 fathoms?",
            "reference_trajectory": json.dumps(
                [{"tool_name": "convert_nautical_units", "tool_input": {"value": 12, "from_unit": "fathoms", "to_unit": "meters"}}]
            ),
        },
        # --- Multi-tool chains (Prompts 9–11) ---
        # Prompt 9: Port lookup + weather check (Cozumel)
        {
            "prompt": "Look up the cruise port in Cozumel, Mexico and then check the current weather there.",
            "reference_trajectory": json.dumps(
                [
                    {"tool_name": "lookup_port", "tool_input": {"query": "cruise port in Cozumel, Mexico"}},
                    {"tool_name": "get_weather", "tool_input": {}},
                ]
            ),
        },
        # Prompt 10: Unit conversion + speed record search
        {
            "prompt": "Our ship is traveling at 22 knots. Convert that to kilometers per hour, and also search for the current speed record for cruise ships.",
            "reference_trajectory": json.dumps(
                [
                    {"tool_name": "convert_nautical_units", "tool_input": {"value": 22, "from_unit": "knots", "to_unit": "kph"}},
                    {"tool_name": "google_search_agent", "tool_input": {"request": "current speed record for cruise ships"}},
                ]
            ),
        },
        # Prompt 11: Port lookup + weather + unit conversion (Nassau)
        {
            "prompt": "Find the cruise port in Nassau, Bahamas, check the weather at that location, and convert 50 nautical miles to kilometers.",
            "reference_trajectory": json.dumps(
                [
                    {"tool_name": "lookup_port", "tool_input": {"query": "cruise port in Nassau, Bahamas"}},
                    {"tool_name": "get_weather", "tool_input": {}},
                    {"tool_name": "convert_nautical_units", "tool_input": {"value": 50, "from_unit": "nautical_miles", "to_unit": "km"}},
                ]
            ),
        },
    ]
    return pd.DataFrame(data)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the Cruise Captain agent"
    )
    parser.add_argument(
        "--experiment-name",
        default="captain-eval",
        help="Vertex AI experiment name (default: captain-eval)",
    )
    args = parser.parse_args()

    # Header panel
    config_table = Table(show_header=False, box=None, padding=(0, 2))
    config_table.add_column("Key", style="bold")
    config_table.add_column("Value")
    config_table.add_row("Project", GOOGLE_CLOUD_PROJECT or "N/A")
    config_table.add_row("Location", GOOGLE_CLOUD_LOCATION)
    config_table.add_row("Experiment", args.experiment_name)
    console.print(Panel(config_table, title="Cruise Captain Agent Evaluation", border_style="blue"))

    eval_dataset = build_eval_dataset()
    console.print(f"\nEval dataset: [bold]{len(eval_dataset)}[/bold] prompts\n")

    trajectory_metrics = [
        "trajectory_exact_match",
        "trajectory_in_order_match",
        "trajectory_any_order_match",
        "trajectory_precision",
        "trajectory_recall",
    ]
    response_metrics = [
        "coherence",       # How logically consistent is the response
        "fluency",         # How natural and readable is the response
        "safety"           # How safe is the response
    ]

    eval_task = EvalTask(
        dataset=eval_dataset,
        metrics=trajectory_metrics + response_metrics,
        experiment=args.experiment_name,
    )

    console.print("[bold cyan]Running evaluation...[/bold cyan]")
    result = eval_task.evaluate(runnable=agent_runnable)

    # Summary metrics table
    summary = result.summary_metrics
    summary_table = Table(title="Summary Metrics", box=box.ROUNDED)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", justify="right")
    summary_table.add_column("Threshold", justify="right", style="dim")
    summary_table.add_column("Status", justify="center")

    for metric_name, value in sorted(summary.items()):
        threshold = THRESHOLDS.get(metric_name)
        if threshold is not None:
            passed = value is not None and value >= threshold
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            threshold_str = str(threshold)
        else:
            status = "-"
            threshold_str = "-"
        summary_table.add_row(
            metric_name,
            f"{value}" if value is not None else "N/A",
            threshold_str,
            status,
        )

    console.print()
    console.print(summary_table)

    # Per-row results
    console.print()
    metrics_df = result.metrics_table
    metric_cols = [
        col for col in metrics_df.columns
        if col not in ("prompt", "response", "reference_trajectory", "predicted_trajectory")
    ]

    for idx, row in metrics_df.iterrows():
        row_table = Table(show_header=False, box=None, padding=(0, 2))
        row_table.add_column("Field", style="bold")
        row_table.add_column("Value")

        prompt_text = str(row.get("prompt", "N/A"))
        row_table.add_row("Prompt", prompt_text)

        if "response" in row:
            row_table.add_row("Response", str(row["response"]))

        for col in metric_cols:
            val = row[col]
            row_table.add_row(col, str(val))

        console.print(Panel(row_table, title=f"Prompt {idx + 1}", border_style="dim"))

    console.print()
    if not check_eval_results(result):
        sys.exit(1)


if __name__ == "__main__":
    main()
