import { useState, useEffect, useCallback, useRef } from 'react';
import { ChatMessage } from '../types/adk';
import { A2UIMessage } from '../types/a2ui';
import { SAMPLE_STAGE_1_A2UI, SAMPLE_PRD_A2UI } from '../data/sampleA2UI';

const APP_NAME = 'project_ideator';
const USER_ID = 'user';

export function useAgentChat() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'streaming' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Initialize ADK Session
  const initSession = useCallback(async () => {
    setStatus('connecting');
    setErrorMessage(null);
    try {
      const res = await fetch(`/apps/${APP_NAME}/users/${USER_ID}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      setSessionId(data.id);
      setStatus('connected');

      // Clean welcome message
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: '👋 Welcome to the **Project Ideator**! What software idea or developer tool would you like to build? Type your idea below or pick a quick suggestion to begin.',
          timestamp: new Date(),
        },
      ]);
      return data.id;
    } catch (err: any) {
      console.warn('ADK server connection notice:', err);
      setStatus('error');
      setErrorMessage(err.message || 'Cannot connect to ADK server on port 8000');
      // Set offline-friendly welcome message
      setMessages([
        {
          id: 'welcome_offline',
          role: 'assistant',
          content: '👋 Welcome to **Project Ideator**!\n\n*(Note: ADK backend at `localhost:8000` is currently offline. You can run `uv run adk web --port 8000 .` in your terminal to connect, or click "Stage 1 Mock" / "PRD Mock" above to test the A2UI elements directly in chat.)*',
          timestamp: new Date(),
        },
      ]);
      return null;
    }
  }, []);

  useEffect(() => {
    initSession();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [initSession]);

  // Clean conversational text and deduplicate multi-step tool call repeats
  const cleanChatContent = (rawText: string, hasA2UI: boolean): string => {
    let text = rawText.replace(/<a2ui-json>[\s\S]*?<\/a2ui-json>/g, '').trim();

    // Deduplicate exact repeating halves caused by multi-step tool SSE concatenation
    const len = text.length;
    if (len > 30) {
      const half = Math.floor(len / 2);
      const firstHalf = text.substring(0, half).trim();
      const secondHalf = text.substring(half).trim();
      if (firstHalf === secondHalf) {
        text = firstHalf;
      }
    }

    // If A2UI is present, strip redundant numbered option lists and headers from chat text
    if (hasA2UI) {
      const lines = text.split('\n');
      const filtered: string[] = [];
      let inOptionBlock = false;

      for (const line of lines) {
        const trimmed = line.trim();
        // Skip stage markdown headers that duplicate the card title
        if (/^#{1,4}\s+Stage\s+\d+/i.test(trimmed)) {
          inOptionBlock = true;
          continue;
        }
        // Skip numbered list items e.g. "1. **Developer...", "2. **AI..."
        if (/^\d+\.\s+\*\*/.test(trimmed)) {
          inOptionBlock = true;
          continue;
        }
        // Skip prompt hints like "*(Pick one or enter..." or "*(Or describe..."
        if (/^\*\([Pp]ick one|[Dd]escribe your own/i.test(trimmed)) {
          continue;
        }
        // Skip bold questions that are already inside the A2UI card
        if (inOptionBlock && /^\*\*(What|Who|Why|What's|Where|Which)/i.test(trimmed)) {
          continue;
        }
        if (inOptionBlock && trimmed === '') {
          continue;
        }
        inOptionBlock = false;
        filtered.push(line);
      }

      const result = filtered.join('\n').trim();
      if (result) return result;
    }

    return text;
  };

  // Extract embedded <a2ui-json> from message text
  const extractA2UI = (rawText: string): { cleanText: string; a2ui: A2UIMessage[] | null } => {
    const match = rawText.match(/<a2ui-json>([\s\S]*?)<\/a2ui-json>/);
    let a2uiList: A2UIMessage[] | null = null;
    if (match && match[1]) {
      try {
        const parsed = JSON.parse(match[1]);
        a2uiList = Array.isArray(parsed) ? parsed : [parsed];
      } catch (e) {
        console.error('Failed to parse <a2ui-json> tag:', e);
      }
    }
    const clean = cleanChatContent(rawText, a2uiList !== null);
    return { cleanText: clean, a2ui: a2uiList };
  };

  // Extract A2UI from tool responses in SSE events
  const extractA2UIFromEvent = (eventData: any): A2UIMessage[] | null => {
    if (eventData.a2ui_messages && Array.isArray(eventData.a2ui_messages)) {
      return eventData.a2ui_messages;
    }
    const fnResponses = eventData.function_responses || eventData.functionResponses || [];
    for (const fr of fnResponses) {
      const resp = fr.response || fr;
      if (resp?.a2ui_payload?.a2ui_messages) {
        return resp.a2ui_payload.a2ui_messages;
      }
      if (resp?.a2ui_messages) {
        return resp.a2ui_messages;
      }
    }
    return null;
  };

  // Send message to agent
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;

      const userMsgId = 'user_' + Date.now();
      const assistantMsgId = 'assistant_' + Date.now();

      // Optimistic user message
      setMessages((prev) => [
        ...prev,
        {
          id: userMsgId,
          role: 'user',
          content: text,
          timestamp: new Date(),
        },
      ]);

      let currentSessionId = sessionId;
      if (!currentSessionId) {
        currentSessionId = await initSession();
        if (!currentSessionId) {
          setMessages((prev) => [
            ...prev,
            {
              id: assistantMsgId,
              role: 'assistant',
              content: '⚠️ ADK backend is not reachable at `localhost:8000`. Please start it with `uv run adk web --port 8000 .` or click **Stage 1 Mock** to preview the A2UI UI elements in chat.',
              timestamp: new Date(),
            },
          ]);
          return;
        }
      }

      setStatus('streaming');
      abortControllerRef.current = new AbortController();

      let accumulatedText = '';
      let detectedA2UI: A2UIMessage[] | null = null;

      try {
        const response = await fetch('/run_sse', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: abortControllerRef.current.signal,
          body: JSON.stringify({
            app_name: APP_NAME,
            user_id: USER_ID,
            session_id: currentSessionId,
            new_message: {
              role: 'user',
              parts: [{ text }],
            },
            streaming: true,
          }),
        });

        if (!response.ok) {
          throw new Error(`Backend error (${response.status} ${response.statusText})`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('Response stream is unavailable.');
        }

        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data:')) continue;
            const jsonStr = trimmed.replace(/^data:\s*/, '');
            if (!jsonStr || jsonStr === '[DONE]') continue;

            try {
              const eventData = JSON.parse(jsonStr);

              // 1. Check for tool A2UI payload
              const toolA2UI = extractA2UIFromEvent(eventData);
              if (toolA2UI) {
                detectedA2UI = toolA2UI;
              }

              // 2. Extract text chunks from parts
              const parts = eventData.content?.parts || [];
              for (const part of parts) {
                if (part.text) {
                  accumulatedText += part.text;
                }
              }

              if (typeof eventData === 'string') {
                accumulatedText += eventData;
              }

              // 3. Extract text tag fallback
              const { cleanText, a2ui } = extractA2UI(accumulatedText);
              if (a2ui) {
                detectedA2UI = a2ui;
              }

              // Update assistant message in real time
              setMessages((prev) => {
                const existingIndex = prev.findIndex((m) => m.id === assistantMsgId);
                const displayMsg: ChatMessage = {
                  id: assistantMsgId,
                  role: 'assistant',
                  content: cleanText || accumulatedText,
                  timestamp: new Date(),
                  a2uiMessages: detectedA2UI || undefined,
                };

                if (existingIndex >= 0) {
                  const updated = [...prev];
                  updated[existingIndex] = displayMsg;
                  return updated;
                } else {
                  return [...prev, displayMsg];
                }
              });
            } catch (err) {
              // Ignore non-json chunks
            }
          }
        }

        const { cleanText, a2ui } = extractA2UI(accumulatedText);
        if (a2ui) {
          detectedA2UI = a2ui;
        }

        setMessages((prev) => {
          const existingIndex = prev.findIndex((m) => m.id === assistantMsgId);
          const finalMsg: ChatMessage = {
            id: assistantMsgId,
            role: 'assistant',
            content: cleanText || accumulatedText || 'Processed response.',
            timestamp: new Date(),
            a2uiMessages: a2ui || detectedA2UI || undefined,
          };
          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = finalMsg;
            return updated;
          }
          return [...prev, finalMsg];
        });

        setStatus('connected');
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        console.error('Chat error:', err);
        setStatus('error');
        setErrorMessage(err.message);
        setMessages((prev) => [
          ...prev,
          {
            id: assistantMsgId,
            role: 'assistant',
            content: `⚠️ Failed to get response: ${err.message}`,
            timestamp: new Date(),
          },
        ]);
      }
    },
    [sessionId, initSession]
  );

  const loadMockStage = () => {
    setMessages((prev) => [
      ...prev,
      {
        id: 'mock_stage_' + Date.now(),
        role: 'assistant',
        content: 'Here is an interactive Stage 1 Grilling question generated with A2UI:',
        timestamp: new Date(),
        a2uiMessages: SAMPLE_STAGE_1_A2UI,
      },
    ]);
  };

  const loadMockPrd = () => {
    setMessages((prev) => [
      ...prev,
      {
        id: 'mock_prd_' + Date.now(),
        role: 'assistant',
        content: 'Here is the final synthesized Product Requirements Document and export card:',
        timestamp: new Date(),
        a2uiMessages: SAMPLE_PRD_A2UI,
      },
    ]);
  };

  const resetSession = () => {
    setMessages([]);
    initSession();
  };

  return {
    sessionId,
    messages,
    status,
    errorMessage,
    sendMessage,
    loadMockStage,
    loadMockPrd,
    resetSession,
  };
}
