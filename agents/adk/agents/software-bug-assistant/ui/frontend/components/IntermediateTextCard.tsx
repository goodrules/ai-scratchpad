"use client";

import { useState } from "react";
import { Highlight, themes } from "prism-react-renderer";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface IntermediateTextCardProps {
  text: string;
  agentName: string;
}

export default function IntermediateTextCard({ text, agentName }: IntermediateTextCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="my-1 rounded-lg bg-slate-800/60 border border-slate-700/40 overflow-hidden text-sm">
      <div
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-700/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-base leading-none">💬</span>
        <span className="font-mono text-slate-300 font-medium">Agent Text</span>
        <span className="ml-auto text-xs text-slate-500 italic">{agentName}</span>
        <span className="text-slate-500 text-xs ml-2">{expanded ? "▲" : "▼"}</span>
      </div>
      {expanded && (
        <div className="px-3 pb-3 border-t border-slate-700/40">
          <div className="mt-2 prose prose-invert prose-xs max-w-none text-slate-300 leading-relaxed text-xs">
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
                          style={{ ...style, margin: 0, fontSize: "0.7rem", borderRadius: "0.375rem", padding: "0.5rem" }}
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
                      className="bg-slate-900 px-1 py-0.5 rounded text-slate-200 text-xs font-mono"
                      {...props}
                    >
                      {children}
                    </code>
                  );
                },
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
      )}
    </div>
  );
}
