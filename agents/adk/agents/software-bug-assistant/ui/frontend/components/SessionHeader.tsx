"use client";

interface SessionHeaderProps {
  onNewSession: () => void;
  sessionId?: string;
}

export default function SessionHeader({ onNewSession, sessionId }: SessionHeaderProps) {
  return (
    <header className="flex items-center justify-between px-6 py-3 bg-slate-900/80 border-b border-slate-700/60 backdrop-blur-sm shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-sm font-bold">
          B
        </div>
        <div>
          <h1 className="text-slate-100 font-semibold text-base leading-none">
            Software Bug Assistant
          </h1>
          {sessionId && (
            <p className="text-slate-500 text-xs mt-0.5 font-mono">
              session: {sessionId.slice(0, 8)}…
            </p>
          )}
        </div>
      </div>
      <button
        onClick={onNewSession}
        className="px-3 py-1.5 text-sm rounded-lg bg-slate-700/60 hover:bg-slate-600/60 text-slate-300 hover:text-slate-100 border border-slate-600/40 hover:border-slate-500/60 transition-all duration-150 font-medium"
      >
        New Session
      </button>
    </header>
  );
}
