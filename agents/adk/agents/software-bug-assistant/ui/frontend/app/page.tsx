"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ActivitySidebar from "../components/ActivitySidebar";
import ChatContainer from "../components/ChatContainer";
import ChatInput from "../components/ChatInput";
import SessionHeader from "../components/SessionHeader";
import { createSession, deleteSession, sendMessage } from "../lib/api";
import { parseEvent } from "../lib/event-parser";
import { AgentTextMessage, ChatMessage } from "../lib/types";

const SIDEBAR_TYPES = new Set(["tool-call", "tool-response", "handoff", "code-execution", "intermediate-text"]);
const MAIN_TYPES = new Set(["user", "agent-text", "streaming", "error", "artifact", "inline-image"]);

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track current streaming message ID and current agent
  const streamingMsgIdRef = useRef<string | null>(null);
  const currentAgentRef = useRef<string>("software_assistant");
  const abortRef = useRef<AbortController | null>(null);

  // Derive main chat messages (user + agent text/streaming + errors)
  const mainMessages = useMemo(
    () => messages.filter((m) => MAIN_TYPES.has(m.type)),
    [messages]
  );

  // Derive sidebar steps (tool calls, responses, handoffs, code execution)
  const sidebarSteps = useMemo(
    () => messages.filter((m) => SIDEBAR_TYPES.has(m.type)),
    [messages]
  );

  // Show thinking indicator when streaming but no agent text has arrived yet
  const isThinking = useMemo(() => {
    if (!isStreaming) return false;
    const last = mainMessages[mainMessages.length - 1];
    return !last || last.type === "user";
  }, [isStreaming, mainMessages]);

  // Initialize session on mount
  useEffect(() => {
    initSession();
    return () => {
      abortRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function initSession() {
    try {
      const id = await createSession();
      setSessionId(id);
      setMessages([]);
      streamingMsgIdRef.current = null;
      currentAgentRef.current = "software_assistant";
    } catch (err) {
      setError(`Failed to create session: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  async function handleNewSession() {
    abortRef.current?.abort();
    if (sessionId) {
      await deleteSession(sessionId).catch(() => {});
    }
    setMessages([]);
    setIsStreaming(false);
    setError(null);
    await initSession();
  }

  const handleSend = useCallback(
    (text: string) => {
      if (!sessionId || isStreaming) return;

      // Add user message optimistically
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        type: "user",
        timestamp: Date.now(),
        text,
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      setError(null);

      const controller = sendMessage(
        sessionId,
        text,
        // onEvent
        (event) => {
          // Track agent changes
          if (event.author) {
            currentAgentRef.current = event.author;
          }

          const result = parseEvent(
            event,
            currentAgentRef.current,
            streamingMsgIdRef.current
          );

          setMessages((prev) => {
            let next = [...prev];

            // Append new messages
            if (result.newMessages.length > 0) {
              // Check if one of the new messages is a streaming bubble
              const streamingNew = result.newMessages.find(
                (m) => m.type === "streaming"
              );
              if (streamingNew) {
                streamingMsgIdRef.current = streamingNew.id;
              }
              next = [...next, ...result.newMessages];
            }

            // Append text to existing streaming bubble
            if (result.streamingUpdateId && result.streamingAppendText) {
              next = next.map((m) =>
                m.id === result.streamingUpdateId
                  ? {
                      ...m,
                      text:
                        (m as AgentTextMessage).text +
                        result.streamingAppendText,
                    }
                  : m
              );
            }

            // Finalize streaming bubble
            if (result.finalizeStreamingId) {
              next = next.map((m) => {
                if (m.id === result.finalizeStreamingId) {
                  const updated = { ...m, type: "agent-text" as const, isStreaming: false } as AgentTextMessage;
                  // If there's also text to append
                  if (result.streamingAppendText && !result.streamingUpdateId) {
                    (updated as AgentTextMessage).text =
                      (m as AgentTextMessage).text + result.streamingAppendText;
                  }
                  return updated;
                }
                return m;
              });
            }

            return next;
          });
          // Synchronously clear the ref so the next SSE event sees null immediately
          // (setMessages updater runs asynchronously during React's render cycle)
          if (result.finalizeStreamingId) {
            streamingMsgIdRef.current = null;
          }
        },
        // onComplete
        () => {
          // Finalize any open streaming bubble
          if (streamingMsgIdRef.current) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingMsgIdRef.current
                  ? { ...m, type: "agent-text" as const, isStreaming: false } as AgentTextMessage
                  : m
              )
            );
            streamingMsgIdRef.current = null;
          }
          // Reclassify agent-text messages from this turn (after the last user
          // message) except the final one as intermediate-text.
          setMessages((prev) => {
            const lastUserIdx = prev.reduce(
              (acc, m, i) => (m.type === "user" ? i : acc), -1
            );
            const agentTextIndices = prev
              .map((m, i) => (i > lastUserIdx && m.type === "agent-text" ? i : -1))
              .filter((i) => i !== -1);
            if (agentTextIndices.length <= 1) return prev;
            const keepIndex = agentTextIndices[agentTextIndices.length - 1];
            return prev.map((m, i) =>
              m.type === "agent-text" && i !== keepIndex && i > lastUserIdx
                ? { ...m, type: "intermediate-text" as const }
                : m
            );
          });
          setIsStreaming(false);
        },
        // onError
        (err) => {
          setError(err.message);
          setIsStreaming(false);
          streamingMsgIdRef.current = null;
        }
      );

      abortRef.current = controller;
    },
    [sessionId, isStreaming]
  );

  return (
    <div className="flex flex-col h-full bg-slate-950">
      <SessionHeader onNewSession={handleNewSession} sessionId={sessionId ?? undefined} />

      {error && (
        <div className="px-4 py-2 bg-red-950/50 border-b border-red-800/50 text-red-300 text-sm">
          {error}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <ChatContainer messages={mainMessages} isThinking={isThinking} sessionId={sessionId} />
        <ActivitySidebar steps={sidebarSteps} />
      </div>

      <ChatInput onSend={handleSend} disabled={isStreaming || !sessionId} />
    </div>
  );
}
