import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '../types/adk';
import { Bot, User } from 'lucide-react';
import { A2UISurface } from './a2ui/A2UISurface';

interface ChatThreadProps {
  messages: ChatMessage[];
  status: string;
  onDispatchAction: (text: string) => void;
}

export const ChatThread: React.FC<ChatThreadProps> = ({
  messages,
  status,
  onDispatchAction,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, status]);

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto px-4 py-6 space-y-6 scroll-smooth"
    >
      {messages.map((msg, idx) => {
        const isUser = msg.role === 'user';
        const isLastMessage = idx === messages.length - 1;

        return (
          <div
            key={msg.id}
            className={`flex items-start gap-3.5 max-w-3xl mx-auto ${
              isUser ? 'flex-row-reverse' : 'flex-row'
            }`}
          >
            {/* Minimal Avatar */}
            <div
              className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-semibold ${
                isUser
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-800 text-indigo-400 border border-slate-700'
              }`}
            >
              {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble & Inline Surface */}
            <div className={`flex flex-col max-w-[88%] ${isUser ? 'items-end' : 'items-start'}`}>
              <div
                className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                  isUser
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : 'bg-slate-800/90 text-slate-100 border border-slate-700/80 rounded-tl-none'
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>

              {/* In-Chat A2UI Element */}
              {msg.a2uiMessages && msg.a2uiMessages.length > 0 && (
                <div className="w-full">
                  <A2UISurface
                    messages={msg.a2uiMessages}
                    onDispatchAction={onDispatchAction}
                    disabled={status === 'streaming' || !isLastMessage}
                  />
                </div>
              )}
            </div>
          </div>
        );
      })}

      {status === 'streaming' && (
        <div className="max-w-3xl mx-auto flex items-center gap-2.5 text-xs text-indigo-400 pl-10">
          <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
          <span>Agent is reasoning and updating A2UI components...</span>
        </div>
      )}
    </div>
  );
};
