"use client";

import { KeyboardEvent, useRef, useState } from "react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSend() {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleInput() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  return (
    <div className="flex items-end gap-3 px-4 py-3 bg-slate-900/80 border-t border-slate-700/60 backdrop-blur-sm shrink-0">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
        placeholder={disabled ? "Waiting for response…" : "Type your message… (Enter to send, Shift+Enter for newline)"}
        rows={1}
        className="flex-1 resize-none rounded-xl bg-slate-800/70 border border-slate-700/50 text-slate-200 placeholder-slate-500 px-4 py-3 text-sm focus:outline-none focus:border-blue-600/60 focus:ring-1 focus:ring-blue-600/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed max-h-40 leading-relaxed"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        className="shrink-0 px-4 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium text-sm transition-all duration-150 disabled:cursor-not-allowed"
      >
        Send
      </button>
    </div>
  );
}
