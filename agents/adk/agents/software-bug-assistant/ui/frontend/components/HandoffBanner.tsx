"use client";

interface HandoffBannerProps {
  fromAgent: string;
  toAgent: string;
}

export default function HandoffBanner({ fromAgent, toAgent }: HandoffBannerProps) {
  const isEscalate = !toAgent || toAgent === fromAgent;

  return (
    <div className="my-1 rounded-lg bg-slate-800/60 border border-slate-700/40 overflow-hidden text-xs">
      <div className="px-3 py-1.5 flex items-center gap-2">
        <span className="text-indigo-400 font-medium">&#8644; Handoff</span>
        <span className="text-slate-500">|</span>
        {isEscalate ? (
          <span className="text-slate-400">escalate &rarr; <span className="text-blue-300">{fromAgent}</span></span>
        ) : (
          <span className="text-slate-400">
            <span className="text-blue-300">{fromAgent}</span>
            <span className="mx-1 opacity-60">&rarr;</span>
            <span className="text-purple-300">{toAgent}</span>
          </span>
        )}
      </div>
    </div>
  );
}
