import React from 'react';
import { RefreshCw, Play, Sparkles, Terminal } from 'lucide-react';

interface HeaderProps {
  status: 'idle' | 'connecting' | 'connected' | 'streaming' | 'error';
  onReset: () => void;
  onLoadMockStage: () => void;
  onLoadMockPrd: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  onReset,
  onLoadMockStage,
  onLoadMockPrd,
}) => {
  const getStatusDot = () => {
    switch (status) {
      case 'connected':
        return (
          <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Backend Connected
          </span>
        );
      case 'streaming':
        return (
          <span className="flex items-center gap-1.5 text-xs text-indigo-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
            Streaming...
          </span>
        );
      case 'connecting':
        return (
          <span className="flex items-center gap-1.5 text-xs text-amber-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            Connecting...
          </span>
        );
      case 'error':
      default:
        return (
          <span className="flex items-center gap-1.5 text-xs text-rose-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            Backend Offline
          </span>
        );
    }
  };

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-20 px-4 py-3">
      <div className="max-w-3xl mx-auto flex items-center justify-between gap-3">
        {/* Left: App Title */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-sm">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-semibold text-white tracking-tight">
                Project Ideator
              </h1>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono text-indigo-300 bg-indigo-950/80 border border-indigo-800/60">
                A2UI
              </span>
            </div>
          </div>
        </div>

        {/* Right: Status & Quick Controls */}
        <div className="flex items-center gap-3">
          {getStatusDot()}

          <div className="flex items-center gap-1.5 pl-2 border-l border-slate-800">
            <button
              onClick={onLoadMockStage}
              title="Test A2UI: Render Stage 1 Grilling Card in Chat"
              className="px-2 py-1 text-xs text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 rounded-md border border-slate-700/70 transition-colors flex items-center gap-1"
            >
              <Play className="w-3 h-3 text-indigo-400" />
              Stage 1 Mock
            </button>
            <button
              onClick={onLoadMockPrd}
              title="Test A2UI: Render Stage 5 PRD Card in Chat"
              className="px-2 py-1 text-xs text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 rounded-md border border-slate-700/70 transition-colors flex items-center gap-1"
            >
              <Sparkles className="w-3 h-3 text-amber-400" />
              PRD Mock
            </button>
            <button
              onClick={onReset}
              title="Reset Chat Session"
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
