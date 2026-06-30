"use client";

import { useState } from "react";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { useCoAgent, useCoAgentStateRender } from "@copilotkit/react-core";
import { PipelineTimeline } from "@/components/PipelineTimeline";
import { LocationReport } from "@/components/LocationReport";
import { CompetitorCard } from "@/components/CompetitorCard";
import { MarketCard } from "@/components/MarketCard";
import { AlternativeLocations } from "@/components/AlternativeLocations";
import { ArtifactViewer } from "@/components/ArtifactViewer";
import type { AgentState } from "@/lib/types";

const EXAMPLES: Record<"retail" | "datacenter", string> = {
  retail: `Hi! I'm your AI-powered location strategy assistant.

Tell me about your business and where you'd like to open, and I'll analyze the market, map competitors, and provide strategic recommendations.

**Try these examples:**
- "I want to open a coffee shop in Indiranagar, Bangalore"
- "Analyze the market for a new gym in downtown Seattle"
- "Where should I open a bakery in San Francisco's Mission District?"`,
  datacenter: `Hi! I'm your AI-powered location strategy assistant.

Tell me about your site selection needs and I'll analyze the market, map facilities, and provide strategic recommendations.

**Try these examples:**
- "I want to build a 50MW hyperscale data center in Northern Virginia"
- "Analyze the Dallas-Fort Worth metro for colocation facilities"
- "Where should I deploy edge data centers in Phoenix, Arizona?"`,
};

export default function Home() {
  const [promptStyle, setPromptStyle] = useState<"retail" | "datacenter">("datacenter");

  // Connect to agent state - this receives STATE_SNAPSHOT and STATE_DELTA events
  // The name must match the agent name in route.ts and backend app_name
  const { state, setState } = useCoAgent<AgentState>({
    name: "ai_location_strategy",
  });

  const handleStyleChange = (style: "retail" | "datacenter") => {
    setPromptStyle(style);
    setState({ ...state, prompt_style: style });
  };

  // Render state in chat as generative UI
  // This creates rich UI components that appear inline in the chat
  // Simplified to show only current stage indicator (main dashboard shows full timeline)
  useCoAgentStateRender<AgentState>({
    name: "ai_location_strategy",
    render: ({ state }) => {
      if (!state) return null;

      // Early return during intake to avoid showing JSON output
      if (!state.pipeline_stage || state.pipeline_stage === "intake" || !state.stages_completed?.length) {
        if (state.target_location) {
          return (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                <span className="text-blue-700 text-sm font-medium">
                  Parsing your request...
                </span>
              </div>
            </div>
          );
        }
        return null;
      }

      // Show simplified progress indicator in chat
      const stageLabels: Record<string, string> = {
        market_research: "Researching market trends...",
        competitor_mapping: "Mapping facilities...",
        gap_analysis: "Analyzing market gaps...",
        strategy_synthesis: "Synthesizing strategy...",
        report_generation: "Generating executive report...",
        infographic_generation: "Creating infographic...",
        map_generation: "Generating interactive map...",
      };

      const currentLabel = stageLabels[state.pipeline_stage] || `Processing ${state.pipeline_stage}...`;
      const completedCount = state.stages_completed?.length || 0;

      return (
        <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
              <span className="text-gray-700 text-sm">{currentLabel}</span>
            </div>
            <span className="text-xs text-gray-500">
              {completedCount}/8 complete
            </span>
          </div>
        </div>
      );
    },
  });

  return (
    <CopilotSidebar
      key={promptStyle}
      defaultOpen={true}
      clickOutsideToClose={false}
      labels={{
        title: "Location Strategy",
        initial: EXAMPLES[promptStyle],
      }}
    >
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        <div className="max-w-5xl mx-auto p-8">
          {/* Header */}
          <header className="mb-8">
            <div className="flex items-center gap-4 mb-2">
              <h1 className="text-4xl font-bold text-gray-900">
                AI Location Strategy
              </h1>
              <select
                value={promptStyle}
                onChange={(e) => handleStyleChange(e.target.value as "retail" | "datacenter")}
                className="px-3 py-1.5 text-sm font-medium bg-white border border-gray-300 rounded-lg shadow-sm cursor-pointer hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              >
                <option value="datacenter">Data Center</option>
                <option value="retail">Retail</option>
              </select>
            </div>
            <p className="text-gray-600">
              Powered by Google ADK + Gemini 3 | Multi-Agent Pipeline
            </p>
          </header>

          {/* Pipeline Timeline - shown when analysis is in progress */}
          {(state?.target_location || state?.pipeline_stage) && (
            <div className="mb-8">
              <PipelineTimeline
                state={state}
                currentStage={state.pipeline_stage}
                completedStages={state.stages_completed || []}
              />
            </div>
          )}

          {/* Detailed Report Cards - shown when analysis is complete */}
          {state?.strategic_report && (
            <div className="space-y-6">
              <LocationReport report={state.strategic_report} />

              <div className="grid md:grid-cols-2 gap-6">
                <CompetitorCard
                  competition={
                    state.strategic_report.top_recommendation.competition
                  }
                />
                <MarketCard
                  market={state.strategic_report.top_recommendation.market}
                />
              </div>

              {/* Alternative Locations */}
              {state.strategic_report.alternative_locations?.length > 0 && (
                <AlternativeLocations
                  locations={state.strategic_report.alternative_locations}
                />
              )}

              {/* Key Insights */}
              <div className="bg-white rounded-xl shadow-sm border p-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <span className="text-xl">💡</span>
                  Key Insights
                </h3>
                <ul className="space-y-2">
                  {state.strategic_report.key_insights.map((insight, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-3 text-gray-700"
                    >
                      <span className="text-blue-500 mt-1">•</span>
                      {insight}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Artifact Viewer - HTML Report, Infographic, and Interactive Map */}
              {(state.html_report_content || state.infographic_base64 || state.map_html_content) && (
                <ArtifactViewer
                  htmlReport={state.html_report_content}
                  infographic={state.infographic_base64}
                  mapHtml={state.map_html_content}
                />
              )}
            </div>
          )}

          {/* Welcome state - shown when no analysis is in progress */}
          {!state?.target_location && (
            <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
              <div className="text-7xl mb-6">{promptStyle === "retail" ? "🏪" : "🌐"}</div>
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                {promptStyle === "retail" ? "Find Your Optimal Location" : "Find Your Optimal Site"}
              </h2>
              <p className="text-gray-600 max-w-lg mx-auto mb-8 text-lg">
                {promptStyle === "retail"
                  ? "Describe your business and target location in the chat, and I'll run a comprehensive analysis using live market data, competitor mapping, and AI-powered strategy recommendations."
                  : "Describe your site selection needs in the chat, and I'll run a comprehensive analysis using live market data, facility mapping, and AI-powered strategy recommendations."}
              </p>

              <div className="grid md:grid-cols-3 gap-4 max-w-2xl mx-auto">
                <FeatureCard
                  icon="🔍"
                  title="Market Research"
                  description={promptStyle === "retail"
                    ? "Live web search for demographics, trends, and commercial data"
                    : "Live web search for market data and regional analysis"}
                />
                <FeatureCard
                  icon="📍"
                  title={promptStyle === "retail" ? "Competitor Mapping" : "Facility Mapping"}
                  description={promptStyle === "retail"
                    ? "Google Maps API for real competitor locations and ratings"
                    : "Google Maps API for real facility and competitor locations"}
                />
                <FeatureCard
                  icon="🧠"
                  title="AI Strategy"
                  description={promptStyle === "retail"
                    ? "Extended reasoning for strategic location recommendations"
                    : "Extended reasoning for strategic site recommendations"}
                />
              </div>
            </div>
          )}
        </div>
      </main>
    </CopilotSidebar>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div className="p-4 bg-gray-50 rounded-lg text-left">
      <div className="text-2xl mb-2">{icon}</div>
      <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
}
