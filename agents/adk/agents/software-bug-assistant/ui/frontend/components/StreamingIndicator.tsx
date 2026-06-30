"use client";

export default function StreamingIndicator() {
  return (
    <span className="inline-flex items-center gap-1 ml-2">
      <span className="streaming-dot w-1.5 h-1.5 rounded-full bg-blue-400 inline-block" />
      <span className="streaming-dot w-1.5 h-1.5 rounded-full bg-blue-400 inline-block" />
      <span className="streaming-dot w-1.5 h-1.5 rounded-full bg-blue-400 inline-block" />
    </span>
  );
}
