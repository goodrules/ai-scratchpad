"use client";

import { useEffect, useRef } from "react";
import {
  AgentTextMessage,
  ArtifactMessage,
  ChatMessage,
  ErrorMessage,
  InlineImageMessage,
  UserMessage,
} from "../lib/types";
import AgentMessage from "./AgentMessage";
import ArtifactImage from "./ArtifactImage";
import ErrorBanner from "./ErrorBanner";

interface ChatContainerProps {
  messages: ChatMessage[];
  isThinking?: boolean;
  sessionId?: string | null;
}

function UserBubble({ msg }: { msg: UserMessage }) {
  return (
    <div className="flex justify-end my-1">
      <div className="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-tr-sm bg-blue-600/80 text-white text-sm leading-relaxed whitespace-pre-wrap">
        {msg.text}
      </div>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex flex-col gap-1.5 my-1">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-400 border border-slate-600/40">
          software_assistant
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-1">
          <span className="streaming-dot w-1.5 h-1.5 rounded-full bg-slate-500 inline-block" />
          <span className="streaming-dot w-1.5 h-1.5 rounded-full bg-slate-500 inline-block" />
          <span className="streaming-dot w-1.5 h-1.5 rounded-full bg-slate-500 inline-block" />
        </span>
        <span className="text-xs text-slate-600">Working…</span>
      </div>
    </div>
  );
}

export default function ChatContainer({ messages, isThinking, sessionId }: ChatContainerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  function renderMessage(msg: ChatMessage) {
    switch (msg.type) {
      case "user":
        return <UserBubble key={msg.id} msg={msg as UserMessage} />;

      case "agent-text":
      case "streaming": {
        const m = msg as AgentTextMessage;
        return (
          <AgentMessage
            key={msg.id}
            text={m.text}
            agentName={m.agentName}
            isStreaming={m.isStreaming}
          />
        );
      }

      case "artifact": {
        const m = msg as ArtifactMessage;
        if (!sessionId) return null;
        return (
          <ArtifactImage
            key={msg.id}
            filename={m.filename}
            sessionId={sessionId}
            agentName={m.agentName}
          />
        );
      }

      case "inline-image": {
        const m = msg as InlineImageMessage;
        return (
          <div key={msg.id} className="flex flex-col gap-1.5 my-1">
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-400 border border-slate-600/40 w-fit">
              {m.agentName}
            </span>
            <img
              src={`data:${m.mimeType};base64,${m.data}`}
              alt="Generated chart"
              className="max-w-full rounded-lg border border-slate-700/50"
            />
          </div>
        );
      }

      case "error": {
        const m = msg as ErrorMessage;
        return (
          <ErrorBanner
            key={msg.id}
            errorCode={m.errorCode}
            errorMessage={m.errorMessage}
          />
        );
      }

      default:
        return null;
    }
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  return (
    <div className="flex-1 overflow-y-auto chat-scroll px-4 py-4">
      {messages.length === 0 && !isThinking && (
        <div className="flex flex-col items-center justify-center h-full text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-2xl font-bold mb-4">
            B
          </div>
          <h2 className="text-slate-300 font-semibold text-lg mb-2">
            Software Bug Assistant
          </h2>
          <p className="text-slate-500 text-sm max-w-sm">
            Ask me to find tickets, debug issues, search documentation, or
            analyze bug patterns. I can query the database, search GitHub and
            Stack Overflow, and run data analysis.
          </p>
          <div className="mt-6 grid grid-cols-1 gap-2 text-sm text-left max-w-sm w-full">
            {[
              "Find tickets related to login failures",
              "Show all open P1 tickets and analyze priority distribution",
              "Search GitHub for issues about authentication timeout",
              "What is the current date?",
            ].map((suggestion) => (
              <div
                key={suggestion}
                className="px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/40 text-slate-400 text-xs cursor-default"
              >
                {suggestion}
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="max-w-3xl mx-auto space-y-1">
        {messages.map((msg) => renderMessage(msg))}
        {isThinking && <ThinkingIndicator />}
      </div>
      <div ref={bottomRef} />
    </div>
  );
}
