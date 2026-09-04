import React, { useState } from 'react';
import { Send, Sparkles } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
}) => {
  const [text, setText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSendMessage(text);
    setText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="border-t border-slate-800 bg-slate-900/90 backdrop-blur p-4 sticky bottom-0 z-10">
      <div className="max-w-3xl mx-auto flex flex-col gap-2.5">
        {/* Quick starter suggestions */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] text-slate-400 pb-1">
          <span className="shrink-0 flex items-center gap-1 text-slate-400">
            <Sparkles className="w-3 h-3 text-indigo-400" /> Quick ideas:
          </span>
          <button
            type="button"
            onClick={() => onSendMessage('I want to build a CLI for debugging Kubernetes pods.')}
            className="px-2 py-0.5 bg-slate-800/90 hover:bg-slate-700/90 text-slate-300 rounded whitespace-nowrap transition-colors"
          >
            Kubernetes CLI
          </button>
          <button
            type="button"
            onClick={() => onSendMessage('I want to build an automated PR reviewer for Go microservices.')}
            className="px-2 py-0.5 bg-slate-800/90 hover:bg-slate-700/90 text-slate-300 rounded whitespace-nowrap transition-colors"
          >
            PR Reviewer
          </button>
          <button
            type="button"
            onClick={() => onSendMessage('I want to build a tool that syncs database schemas to TypeScript types.')}
            className="px-2 py-0.5 bg-slate-800/90 hover:bg-slate-700/90 text-slate-300 rounded whitespace-nowrap transition-colors"
          >
            Schema-to-TS
          </button>
        </div>

        {/* Input box */}
        <form onSubmit={handleSubmit} className="flex gap-2 items-center">
          <textarea
            value={text}
            rows={1}
            disabled={disabled}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your project idea or response (Press Enter)..."
            className="flex-1 bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 resize-none transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={disabled || !text.trim()}
            className="h-11 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl font-medium transition-colors flex items-center justify-center shrink-0 shadow-sm"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
