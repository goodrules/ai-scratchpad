"use client";

import { useEffect, useRef } from "react";
import {
  AgentTextMessage,
  ChatMessage,
  CodeExecutionMessage,
  HandoffMessage,
  ToolCallMessage,
  ToolResponseMessage,
} from "../lib/types";
import CodeBlock from "./CodeBlock";
import HandoffBanner from "./HandoffBanner";
import IntermediateTextCard from "./IntermediateTextCard";
import ToolCallCard from "./ToolCallCard";
import ToolResponseCard from "./ToolResponseCard";

interface ActivitySidebarProps {
  steps: ChatMessage[];
}

function renderStep(msg: ChatMessage) {
  switch (msg.type) {
    case "tool-call": {
      const m = msg as ToolCallMessage;
      return (
        <ToolCallCard
          key={msg.id}
          toolName={m.toolName}
          args={m.args}
          agentName={m.agentName}
        />
      );
    }
    case "tool-response": {
      const m = msg as ToolResponseMessage;
      return (
        <ToolResponseCard
          key={msg.id}
          toolName={m.toolName}
          response={m.response}
          agentName={m.agentName}
        />
      );
    }
    case "handoff": {
      const m = msg as HandoffMessage;
      return (
        <HandoffBanner
          key={msg.id}
          fromAgent={m.fromAgent}
          toAgent={m.toAgent}
        />
      );
    }
    case "code-execution": {
      return <CodeBlock key={msg.id} msg={msg as CodeExecutionMessage} />;
    }
    case "intermediate-text": {
      const m = msg as AgentTextMessage;
      return (
        <IntermediateTextCard
          key={msg.id}
          text={m.text}
          agentName={m.agentName}
        />
      );
    }
    default:
      return null;
  }
}

export default function ActivitySidebar({ steps }: ActivitySidebarProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [steps]);

  return (
    <div className="w-80 flex flex-col border-l border-slate-800/60 bg-slate-900/40 shrink-0">
      <div className="px-4 py-3 border-b border-slate-800/60">
        <h2 className="text-slate-400 text-xs font-semibold tracking-widest uppercase">
          Activity
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-3 sidebar-scroll">
        {steps.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-slate-600 text-xs text-center leading-relaxed">
              Agent activity will
              <br />
              appear here
            </p>
          </div>
        ) : (
          <>
            {steps.map((step) => renderStep(step))}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  );
}
