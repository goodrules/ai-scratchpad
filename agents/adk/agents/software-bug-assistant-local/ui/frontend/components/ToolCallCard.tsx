"use client";

import { useState } from "react";

// Tool icon/label mapping for known tools
const TOOL_META: Record<string, { icon: string; label: string }> = {
  // Ticketing / DB tools
  "search-tickets": { icon: "🔍", label: "Search Tickets" },
  "create-ticket": { icon: "➕", label: "Create Ticket" },
  "update-ticket": { icon: "✏️", label: "Update Ticket" },
  "get-ticket": { icon: "🎫", label: "Get Ticket" },
  "list-tickets": { icon: "📋", label: "List Tickets" },
  "delete-ticket": { icon: "🗑️", label: "Delete Ticket" },
  "search_tickets": { icon: "🔍", label: "Search Tickets" },
  "create_ticket": { icon: "➕", label: "Create Ticket" },
  "update_ticket": { icon: "✏️", label: "Update Ticket" },
  "get_ticket": { icon: "🎫", label: "Get Ticket" },
  "list_tickets": { icon: "📋", label: "List Tickets" },
  // Date / misc
  get_current_date: { icon: "📅", label: "Get Current Date" },
  // Search
  google_search: { icon: "🌐", label: "Google Search" },
  search: { icon: "🌐", label: "Web Search" },
  // StackExchange
  search_stack_overflow: { icon: "💬", label: "Search Stack Overflow" },
  search_stack_exchange: { icon: "💬", label: "Search Stack Exchange" },
  // GitHub MCP
  search_repositories: { icon: "🐙", label: "GitHub: Search Repos" },
  search_issues: { icon: "🐛", label: "GitHub: Search Issues" },
  list_issues: { icon: "📌", label: "GitHub: List Issues" },
  get_issue: { icon: "🔎", label: "GitHub: Get Issue" },
  list_pull_requests: { icon: "🔀", label: "GitHub: List PRs" },
  get_pull_request: { icon: "🔀", label: "GitHub: Get PR" },
  // Analysis
  run_python: { icon: "🐍", label: "Run Python" },
  execute_code: { icon: "⚡", label: "Execute Code" },
};

function getToolMeta(name: string): { icon: string; label: string } {
  if (TOOL_META[name]) return TOOL_META[name];
  // Try to infer from name segments
  const lower = name.toLowerCase();
  if (lower.includes("search")) return { icon: "🔍", label: name };
  if (lower.includes("create") || lower.includes("add")) return { icon: "➕", label: name };
  if (lower.includes("update") || lower.includes("edit")) return { icon: "✏️", label: name };
  if (lower.includes("delete") || lower.includes("remove")) return { icon: "🗑️", label: name };
  if (lower.includes("get") || lower.includes("fetch")) return { icon: "📥", label: name };
  if (lower.includes("list")) return { icon: "📋", label: name };
  return { icon: "🔧", label: name };
}

interface ToolCallCardProps {
  toolName: string;
  args: Record<string, unknown>;
  agentName: string;
}

export default function ToolCallCard({ toolName, args, agentName }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  const { icon, label } = getToolMeta(toolName);
  const hasArgs = Object.keys(args).length > 0;

  return (
    <div className="my-1 rounded-lg bg-slate-800/60 border border-slate-700/40 overflow-hidden text-sm">
      <div
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-700/30 transition-colors"
        onClick={() => hasArgs && setExpanded(!expanded)}
      >
        <span className="text-base leading-none">{icon}</span>
        <span className="font-mono text-slate-300 font-medium">{label}</span>
        <span className="text-slate-500 text-xs ml-1">({toolName})</span>
        <span className="ml-auto text-xs text-slate-500 italic">{agentName}</span>
        {hasArgs && (
          <span className="text-slate-500 text-xs ml-2">
            {expanded ? "▲" : "▼"}
          </span>
        )}
      </div>
      {expanded && hasArgs && (
        <div className="px-3 pb-3 border-t border-slate-700/40">
          <pre className="mt-2 text-xs text-slate-300 bg-slate-900/50 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
            {JSON.stringify(args, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
