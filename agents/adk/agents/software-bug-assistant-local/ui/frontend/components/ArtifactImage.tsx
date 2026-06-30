"use client";

import { useEffect, useState } from "react";
import { fetchArtifact } from "../lib/api";

interface ArtifactImageProps {
  filename: string;
  sessionId: string;
  agentName: string;
}

export default function ArtifactImage({ filename, sessionId, agentName }: ArtifactImageProps) {
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchArtifact(sessionId, filename)
      .then(({ mimeType, data }) => {
        if (!mimeType || !data) {
          throw new Error("Missing mimeType or data in artifact response");
        }
        setDataUrl(`data:${mimeType};base64,${data}`);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [sessionId, filename]);

  return (
    <div className="flex flex-col gap-1.5 my-1">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-400 border border-slate-600/40">
          {agentName}
        </span>
      </div>
      <div className="rounded-xl overflow-hidden border border-slate-700/40 bg-slate-900/50 inline-block max-w-full">
        {error ? (
          <div className="px-4 py-3 text-red-400 text-sm">
            Failed to load image: {error}
          </div>
        ) : dataUrl ? (
          <img
            src={dataUrl}
            alt={filename}
            className="max-w-full rounded-xl"
            style={{ maxHeight: "480px", objectFit: "contain" }}
          />
        ) : (
          <div className="px-4 py-6 flex items-center gap-3 text-slate-500 text-sm">
            <span className="inline-flex gap-1">
              <span className="streaming-dot w-1.5 h-1.5 rounded-full bg-slate-600 inline-block" />
              <span className="streaming-dot w-1.5 h-1.5 rounded-full bg-slate-600 inline-block" />
              <span className="streaming-dot w-1.5 h-1.5 rounded-full bg-slate-600 inline-block" />
            </span>
            Loading {filename}…
          </div>
        )}
      </div>
    </div>
  );
}
