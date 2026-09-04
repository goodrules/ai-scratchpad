import React, { useState } from 'react';
import { Copy, Check, X, Code2 } from 'lucide-react';
import { A2UIMessage } from '../types/a2ui';

interface A2UIInspectorProps {
  messages: A2UIMessage[];
  onClose: () => void;
}

export const A2UIInspector: React.FC<A2UIInspectorProps> = ({ messages, onClose }) => {
  const [copied, setCopied] = useState(false);
  const jsonStr = JSON.stringify(messages, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl p-4 flex flex-col h-[520px]">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            A2UI Protocol Inspector ({messages.length} messages)
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied' : 'Copy JSON'}
          </button>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      <pre className="flex-1 overflow-auto bg-slate-900/90 p-3 rounded-xl border border-slate-800 text-xs text-indigo-300/90 font-mono leading-relaxed">
        {jsonStr}
      </pre>
    </div>
  );
};
