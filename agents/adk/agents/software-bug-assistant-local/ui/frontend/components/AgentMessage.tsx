"use client";

import { Highlight, themes } from "prism-react-renderer";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import StreamingIndicator from "./StreamingIndicator";

const AGENT_COLORS: Record<string, string> = {
  software_assistant: "bg-blue-900/50 text-blue-300 border border-blue-700/40",
  analysis_agent: "bg-purple-900/50 text-purple-300 border border-purple-700/40",
};

function getAgentBadgeClass(agentName: string): string {
  return (
    AGENT_COLORS[agentName] ??
    "bg-slate-700/50 text-slate-300 border border-slate-600/40"
  );
}

interface AgentMessageProps {
  text: string;
  agentName: string;
  isStreaming?: boolean;
}

export default function AgentMessage({ text, agentName, isStreaming }: AgentMessageProps) {
  const badgeClass = getAgentBadgeClass(agentName);

  return (
    <div className="flex flex-col gap-1.5 my-1">
      <div className="flex items-center gap-2">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badgeClass}`}>
          {agentName}
        </span>
        {isStreaming && <StreamingIndicator />}
      </div>
      <div className="prose prose-invert prose-sm max-w-none text-slate-200 leading-relaxed">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            code({ inline, className: langClassName, children, ...props }: any) {
              const match = /language-(\w+)/.exec(langClassName || "");
              return !inline && match ? (
                <Highlight
                  theme={themes.vsDark}
                  code={String(children).replace(/\n$/, "")}
                  language={match[1]}
                >
                  {({ className, style, tokens, getLineProps, getTokenProps }) => (
                    <div
                      className={className}
                      style={{ ...style, margin: 0, fontSize: "0.75rem", borderRadius: "0.375rem", padding: "0.75rem" }}
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
              ) : (
                <code
                  className="bg-slate-800 px-1 py-0.5 rounded text-slate-200 text-xs font-mono"
                  {...props}
                >
                  {children}
                </code>
              );
            },
            // Suppress broken image references from the model's text output
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            img({ src, alt, ...props }: any) {
              if (!src || (!src.startsWith("data:image/") && !src.startsWith("http"))) {
                return <span className="text-slate-500 text-xs">[image: {alt ?? "unavailable"}]</span>;
              }
              return <img src={src} alt={alt} className="max-w-full rounded" {...props} />;
            },
            // Style links
            a({ href, children, ...props }) {
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 underline"
                  {...props}
                >
                  {children}
                </a>
              );
            },
          }}
        >
          {text}
        </ReactMarkdown>
      </div>
    </div>
  );
}
