"use client";

import { useState } from "react";
import { Highlight, themes } from "prism-react-renderer";
import { CodeExecutionMessage } from "../lib/types";

export default function CodeBlock({ msg }: { msg: CodeExecutionMessage }) {
  const [expanded, setExpanded] = useState(false);

  // Pure output block (no code)
  if (!msg.code) {
    const isOk = msg.outcome?.includes("OK");
    return (
      <div className="my-1 rounded-lg bg-slate-900/70 border border-slate-700/40 overflow-hidden text-xs">
        <button
          className="w-full px-3 py-1.5 bg-slate-800/60 border-b border-slate-700/40 flex items-center gap-2 text-left hover:bg-slate-700/40 transition-colors"
          onClick={() => setExpanded((v) => !v)}
        >
          <span className="text-green-400 font-mono font-medium">&#10003; Output</span>
          {msg.outcome && (
            <span className={`text-xs ${isOk ? "text-green-400" : "text-red-400"}`}>
              {msg.outcome}
            </span>
          )}
          <span className="ml-auto text-slate-500 text-xs">{expanded ? "▲" : "▼"}</span>
        </button>
        {expanded && (
          <pre className="px-3 py-2 text-slate-300 overflow-x-auto whitespace-pre-wrap">
            {msg.output}
          </pre>
        )}
      </div>
    );
  }

  // Code + optional output
  return (
    <div className="my-1 rounded-lg bg-slate-900/70 border border-slate-700/40 overflow-hidden text-xs">
      <button
        className="w-full px-3 py-1.5 bg-slate-800/60 border-b border-slate-700/40 flex items-center gap-2 text-left hover:bg-slate-700/40 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="text-yellow-400 font-mono font-medium">
          🐍 {msg.language || "Python"}
        </span>
        <span className="text-slate-500 text-xs italic">{msg.agentName}</span>
        <span className="ml-auto text-slate-500 text-xs">{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && (
        <>
          <Highlight
            theme={themes.vsDark}
            code={msg.code}
            language={msg.language || "python"}
          >
            {({ className, style, tokens, getLineProps, getTokenProps }) => (
              <div
                className={className}
                style={{ ...style, margin: 0, fontSize: "0.75rem", padding: "0.5rem 0.75rem" }}
              >
                {tokens.map((line, i) => (
                  <div key={i} {...getLineProps({ line })}>
                    {line.map((token, key) => (
                      <span key={key} {...getTokenProps({ token })} />
                    ))}
                  </div>
                ))}
              </div>
            )}
          </Highlight>
          {msg.output && (
            <>
              <div className="px-3 py-1 bg-slate-800/40 border-t border-slate-700/30 text-green-400 font-mono text-xs">
                Output
                {msg.outcome && (
                  <span
                    className={`ml-2 ${
                      msg.outcome.includes("OK") ? "text-green-400" : "text-red-400"
                    }`}
                  >
                    ({msg.outcome})
                  </span>
                )}
              </div>
              <pre className="px-3 py-2 text-slate-300 overflow-x-auto whitespace-pre-wrap">
                {msg.output}
              </pre>
            </>
          )}
        </>
      )}
    </div>
  );
}
