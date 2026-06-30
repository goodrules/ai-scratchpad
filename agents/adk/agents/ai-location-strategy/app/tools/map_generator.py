# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Interactive Google Maps visualization tool.

Generates a self-contained HTML page with an interactive Google Map
plotting all recommended locations from the strategic analysis.
Uses the Places API to convert location names to coordinates
and the Maps JavaScript API for client-side rendering.

Requires MAPS_API_KEY environment variable (also used by places_search.py).
The Google Cloud project must have Maps JavaScript API and Places API enabled.
"""

import json
import logging
import os
import re

import googlemaps
from ..config import MAPS_API_KEY
from google.adk import Context
from google.genai import types

logger = logging.getLogger("LocationStrategyPipeline")


def _extract_locations(report: dict) -> list[dict]:
    """Extract location entries from the strategic report.

    Returns a list of dicts with keys:
        location_name, area, overall_score, opportunity_type,
        is_top, extra_meta (dict of type-specific metadata)
    """
    locations: list[dict] = []

    top = report.get("top_recommendation", {})
    if top and top.get("location_name"):
        strengths = top.get("strengths", [])
        concerns = top.get("concerns", [])
        locations.append(
            {
                "location_name": top["location_name"],
                "area": top.get("area", ""),
                "overall_score": top.get("overall_score", 0),
                "opportunity_type": top.get("opportunity_type", ""),
                "is_top": True,
                "extra_meta": {
                    "target_customer_segment": top.get(
                        "target_customer_segment", ""
                    ),
                    "estimated_demand_level": top.get(
                        "estimated_demand_level", ""
                    ),
                    "strengths": [
                        s.get("factor", s) if isinstance(s, dict) else str(s)
                        for s in strengths[:3]
                    ],
                    "concerns": [
                        c.get("risk", c) if isinstance(c, dict) else str(c)
                        for c in concerns[:3]
                    ],
                },
            }
        )

    for alt in report.get("alternative_locations", []):
        if alt.get("location_name"):
            locations.append(
                {
                    "location_name": alt["location_name"],
                    "area": alt.get("area", ""),
                    "overall_score": alt.get("overall_score", 0),
                    "opportunity_type": alt.get("opportunity_type", ""),
                    "is_top": False,
                    "extra_meta": {
                        "key_strength": alt.get("key_strength", ""),
                        "key_concern": alt.get("key_concern", ""),
                        "why_not_top": alt.get("why_not_top", ""),
                    },
                }
            )

    return locations


def _clean_location_name(name: str) -> str:
    """Strip zone labels and normalize slashes for better search accuracy.

    Examples:
        "Manassas / Gainesville (Zone C)" -> "Manassas, Gainesville"
        "Ashburn / Sterling (Zone A)"     -> "Ashburn, Sterling"
    """
    name = re.sub(r"\(Zone\s+\w+\)", "", name)
    name = name.replace(" / ", ", ")
    return name.strip()


def _geocode_locations(
    locations: list[dict], gmaps_client: googlemaps.Client
) -> tuple[list[dict], list[str]]:
    """Geocode each location via Places API, returning (geocoded_list, skipped_names)."""
    geocoded: list[dict] = []
    skipped: list[str] = []

    for loc in locations:
        clean_name = _clean_location_name(loc["location_name"])
        query = f"{clean_name}, {loc['area']}"
        try:
            result = gmaps_client.places(query)
            places = result.get("results", [])
            if places:
                geo = places[0]["geometry"]["location"]
                loc["lat"] = geo["lat"]
                loc["lng"] = geo["lng"]
                loc["formatted_address"] = places[0].get(
                    "formatted_address", query
                )
                geocoded.append(loc)
                logger.info(
                    f"  Geocoded: {query} -> ({geo['lat']:.4f}, {geo['lng']:.4f})"
                )
            else:
                skipped.append(loc["location_name"])
                logger.warning(f"  Geocode returned no results for: {query}")
        except Exception as e:
            skipped.append(loc["location_name"])
            logger.warning(f"  Geocode failed for {query}: {e}")

    return geocoded, skipped


def _build_map_html(
    geocoded_locations: list[dict],
    api_key: str,
    target_location: str,
    business_type: str,
) -> str:
    """Build a self-contained HTML page with an interactive Google Map."""

    # Build JavaScript location data
    js_locations = []
    for loc in geocoded_locations:
        # Build metadata HTML for InfoWindow
        meta_lines = []
        if loc["is_top"]:
            meta = loc.get("extra_meta", {})
            if meta.get("target_customer_segment"):
                meta_lines.append(
                    f"<b>Target Segment:</b> {meta['target_customer_segment']}"
                )
            if meta.get("estimated_demand_level"):
                meta_lines.append(
                    f"<b>Demand Level:</b> {meta['estimated_demand_level']}"
                )
            for s in meta.get("strengths", []):
                meta_lines.append(f"<span style='color:#059669'>+ {s}</span>")
            for c in meta.get("concerns", []):
                meta_lines.append(f"<span style='color:#d97706'>- {c}</span>")
        else:
            meta = loc.get("extra_meta", {})
            if meta.get("key_strength"):
                meta_lines.append(
                    f"<span style='color:#059669'>+ {meta['key_strength']}</span>"
                )
            if meta.get("key_concern"):
                meta_lines.append(
                    f"<span style='color:#d97706'>- {meta['key_concern']}</span>"
                )

        meta_html = "<br>".join(meta_lines)

        js_locations.append(
            {
                "name": loc["location_name"],
                "lat": loc["lat"],
                "lng": loc["lng"],
                "address": loc.get("formatted_address", ""),
                "score": loc["overall_score"],
                "opportunity_type": loc["opportunity_type"],
                "is_top": loc["is_top"],
                "meta_html": meta_html,
            }
        )

    locations_json = json.dumps(js_locations, indent=2)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Location Strategy Map - {business_type} in {target_location}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  #map {{ width: 100%; height: 100vh; }}
  .title-bar {{
    position: absolute; top: 10px; left: 50%; transform: translateX(-50%);
    background: white; padding: 12px 24px; border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.15); z-index: 10;
    text-align: center; max-width: 90%;
  }}
  .title-bar h1 {{ font-size: 16px; color: #1e3a8a; margin-bottom: 2px; }}
  .title-bar p {{ font-size: 12px; color: #6b7280; }}
  .legend {{
    position: absolute; bottom: 30px; left: 10px;
    background: white; padding: 12px 16px; border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12); z-index: 10;
    font-size: 13px;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
  .legend-item:last-child {{ margin-bottom: 0; }}
  .legend-dot {{
    width: 14px; height: 14px; border-radius: 50%; border: 2px solid white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }}
  .legend-dot.top {{ background: #059669; }}
  .legend-dot.alt {{ background: #3b82f6; }}
  .iw-content {{ max-width: 280px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  .iw-content h3 {{ font-size: 15px; color: #1e3a8a; margin-bottom: 4px; }}
  .iw-content .address {{ font-size: 12px; color: #6b7280; margin-bottom: 8px; }}
  .iw-content .score {{
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-weight: 600; font-size: 13px; margin-bottom: 4px;
  }}
  .iw-content .score.high {{ background: #d1fae5; color: #065f46; }}
  .iw-content .score.mid {{ background: #fef3c7; color: #92400e; }}
  .iw-content .score.low {{ background: #fee2e2; color: #991b1b; }}
  .iw-content .opp-type {{ font-size: 12px; color: #4b5563; margin-bottom: 6px; }}
  .iw-content .meta {{ font-size: 12px; line-height: 1.5; }}
  .iw-content .top-badge {{
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    background: #059669; color: white; font-size: 11px; font-weight: 600;
    margin-bottom: 6px;
  }}
</style>
</head>
<body>
<div id="map"></div>

<div class="title-bar">
  <h1>{business_type} - Location Strategy Map</h1>
  <p>{target_location}</p>
</div>

<div class="legend">
  <div class="legend-item">
    <div class="legend-dot top"></div>
    <span>Top Recommendation</span>
  </div>
  <div class="legend-item">
    <div class="legend-dot alt"></div>
    <span>Alternative Location</span>
  </div>
</div>

<script>
const LOCATIONS = {locations_json};

function initMap() {{
  const map = new google.maps.Map(document.getElementById("map"), {{
    zoom: 8,
    mapTypeId: "roadmap",
    styles: [
      {{ featureType: "poi", stylers: [{{ visibility: "simplified" }}] }},
      {{ featureType: "transit", stylers: [{{ visibility: "off" }}] }},
    ],
  }});

  const bounds = new google.maps.LatLngBounds();
  let topInfoWindow = null;

  LOCATIONS.forEach(function(loc) {{
    const position = {{ lat: loc.lat, lng: loc.lng }};
    bounds.extend(position);

    const marker = new google.maps.Marker({{
      position: position,
      map: map,
      title: loc.name,
      icon: {{
        path: google.maps.SymbolPath.CIRCLE,
        scale: loc.is_top ? 12 : 9,
        fillColor: loc.is_top ? "#059669" : "#3b82f6",
        fillOpacity: 0.9,
        strokeColor: "#ffffff",
        strokeWeight: 2.5,
      }},
      zIndex: loc.is_top ? 100 : 50,
    }});

    const scoreClass = loc.score >= 75 ? "high" : (loc.score >= 50 ? "mid" : "low");
    const topBadge = loc.is_top ? '<div class="top-badge">TOP RECOMMENDATION</div>' : '';

    const content = '<div class="iw-content">' +
      topBadge +
      '<h3>' + loc.name + '</h3>' +
      '<div class="address">' + loc.address + '</div>' +
      '<span class="score ' + scoreClass + '">Score: ' + loc.score + '/100</span>' +
      '<div class="opp-type">' + loc.opportunity_type + '</div>' +
      (loc.meta_html ? '<div class="meta">' + loc.meta_html + '</div>' : '') +
      '</div>';

    const infoWindow = new google.maps.InfoWindow({{ content: content }});

    marker.addListener("click", function() {{
      infoWindow.open(map, marker);
    }});

    if (loc.is_top) {{
      topInfoWindow = {{ iw: infoWindow, marker: marker }};
    }}
  }});

  map.fitBounds(bounds);

  // Prevent over-zoom for single marker
  google.maps.event.addListenerOnce(map, "bounds_changed", function() {{
    if (map.getZoom() > 14) {{
      map.setZoom(14);
    }}
  }});

  // Auto-open top recommendation InfoWindow
  if (topInfoWindow) {{
    topInfoWindow.iw.open(map, topInfoWindow.marker);
  }}
}}
</script>
<script async defer
  src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap">
</script>
</body>
</html>"""

    return html


async def generate_interactive_map(tool_context: Context) -> dict:
    """Generate an interactive Google Maps visualization of recommended locations.

    This tool reads the strategic_report from session state, geocodes all
    recommended locations, and generates a self-contained HTML page with
    an interactive Google Map. Markers are color-coded: green for the top
    recommendation, blue for alternatives. Each marker has an InfoWindow
    with score, opportunity type, and metadata.

    The generated HTML is saved as an artifact and stored in state for
    the AG-UI frontend to display.

    Args:
        tool_context: ADK ToolContext for accessing state and saving artifacts.

    Returns:
        dict: Status dict with geocoded_count and skipped_locations.
    """
    try:
        # Get API key
        maps_api_key = (
            tool_context.state.get("maps_api_key", "")
            or MAPS_API_KEY
            or os.environ.get("MAPS_API_KEY", "")
        )

        if not maps_api_key:
            return {
                "status": "error",
                "error_message": "Maps API key not found. Set MAPS_API_KEY environment variable or 'maps_api_key' in session state.",
            }

        # Get strategic report from state
        report = tool_context.state.get("strategic_report", {})
        if not report:
            return {
                "status": "error",
                "error_message": "No strategic_report found in state. The strategy synthesis stage must complete first.",
            }

        # Handle Pydantic model, dict, or JSON string
        if hasattr(report, "model_dump"):
            report = report.model_dump()
        elif isinstance(report, str):
            try:
                report = json.loads(report)
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "error_message": "strategic_report is a string but not valid JSON.",
                }

        target_location = report.get(
            "target_location",
            tool_context.state.get("target_location", "Unknown"),
        )
        business_type = report.get(
            "business_type",
            tool_context.state.get("business_type", "Data Center"),
        )

        # Extract locations from report
        locations = _extract_locations(report)
        if not locations:
            return {
                "status": "error",
                "error_message": "No locations found in strategic_report to map.",
            }

        logger.info(
            f"Map generation: found {len(locations)} locations to geocode"
        )

        # Geocode locations
        gmaps_client = googlemaps.Client(key=maps_api_key)
        geocoded, skipped = _geocode_locations(locations, gmaps_client)

        if not geocoded:
            return {
                "status": "error",
                "error_message": f"All {len(locations)} locations failed to geocode. Skipped: {skipped}",
            }

        # Build the interactive map HTML
        map_html = _build_map_html(
            geocoded, maps_api_key, target_location, business_type
        )

        # Save as artifact
        html_artifact = types.Part.from_bytes(
            data=map_html.encode("utf-8"), mime_type="text/html"
        )
        version = await tool_context.save_artifact(
            filename="interactive_map.html", artifact=html_artifact
        )
        logger.info(
            f"Saved interactive map artifact: interactive_map.html (version {version})"
        )

        # Store in state for AG-UI frontend
        tool_context.state["map_html_content"] = map_html

        return {
            "status": "success",
            "message": f"Interactive map generated with {len(geocoded)} locations and saved as 'interactive_map.html'",
            "geocoded_count": len(geocoded),
            "skipped_locations": skipped,
            "artifact_filename": "interactive_map.html",
            "artifact_version": version,
        }

    except Exception as e:
        logger.error(f"Failed to generate interactive map: {e}")
        return {
            "status": "error",
            "error_message": f"Failed to generate interactive map: {e!s}",
        }
