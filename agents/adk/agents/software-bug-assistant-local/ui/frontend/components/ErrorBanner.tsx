"use client";

interface ErrorBannerProps {
  errorCode?: string;
  errorMessage: string;
}

export default function ErrorBanner({ errorCode, errorMessage }: ErrorBannerProps) {
  return (
    <div className="flex items-start gap-2 px-4 py-3 rounded-lg bg-red-950/60 border border-red-700/50 text-red-300 text-sm my-1">
      <span className="text-red-400 font-bold shrink-0">&#9888;</span>
      <div>
        {errorCode && (
          <span className="font-mono text-xs text-red-400 mr-2">[{errorCode}]</span>
        )}
        {errorMessage}
      </div>
    </div>
  );
}
