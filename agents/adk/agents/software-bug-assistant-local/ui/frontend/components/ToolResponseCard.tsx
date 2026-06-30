"use client";

import { useState } from "react";

interface ToolResponseCardProps {
  toolName: string;
  response: Record<string, unknown>;
  agentName: string;
}

export default function ToolResponseCard({ toolName, response, agentName }: ToolResponseCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="my-1 rounded-lg bg-slate-800/40 border border-slate-700/30 overflow-hidden text-sm">
      <div
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-700/20 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-base leading-none text-green-400">&#10003;</span>
        <span className="font-mono text-slate-400 font-medium">{toolName}</span>
        <span className="ml-auto text-xs text-slate-500 italic">{agentName}</span>
        <span className="text-slate-500 text-xs ml-2">
          {expanded ? "Hide response ▲" : "Show response ▼"}
        </span>
      </div>
      {expanded && (
        <div className="px-3 pb-3 border-t border-slate-700/30">
          <pre className="mt-2 text-xs text-slate-400 bg-slate-900/50 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all max-h-64 overflow-y-auto">
            {JSON.stringify(response, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
