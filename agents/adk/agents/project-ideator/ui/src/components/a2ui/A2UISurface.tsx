import React, { useState, useEffect, useMemo } from 'react';
import { A2UIMessage, A2UIComponent } from '../../types/a2ui';
import { A2UIComponentResolver } from './A2UIComponentResolver';
import { Sparkles, Code2, Check, Copy } from 'lucide-react';

interface A2UISurfaceProps {
  messages: A2UIMessage[];
  onDispatchAction: (textToSend: string, meta?: any) => void;
  disabled?: boolean;
}

export const A2UISurface: React.FC<A2UISurfaceProps> = ({
  messages,
  onDispatchAction,
  disabled = false,
}) => {
  const [surfaceId, setSurfaceId] = useState<string>('main');
  const [dataModel, setDataModel] = useState<Record<string, any>>({});
  const [components, setComponents] = useState<A2UIComponent[]>([]);
  const [showJson, setShowJson] = useState(false);
  const [copied, setCopied] = useState(false);

  // Apply sequential A2UI messages to local surface state
  useEffect(() => {
    if (!messages || messages.length === 0) return;

    for (const msg of messages) {
      const create = msg.createSurface || msg.beginRendering;
      if (create) {
        setSurfaceId(create.surfaceId || 'main');
      }

      const updateComp = msg.updateComponents || msg.surfaceUpdate;
      if (updateComp && Array.isArray(updateComp.components)) {
        setComponents(updateComp.components);
      }

      const updateData = msg.updateDataModel || msg.dataModelUpdate;
      if (updateData) {
        setDataModel((prev) => {
          const next = { ...prev };
          if (updateData.path) {
            const parts = updateData.path.split('/').filter(Boolean);
            let curr = next;
            for (let i = 0; i < parts.length - 1; i++) {
              if (!curr[parts[i]] || typeof curr[parts[i]] !== 'object') {
                curr[parts[i]] = {};
              }
              curr = curr[parts[i]];
            }
            if (parts.length > 0) {
              curr[parts[parts.length - 1]] = updateData.value;
            }
          } else if (typeof updateData.value === 'object') {
            Object.assign(next, updateData.value);
          }
          return next;
        });
      }
    }
  }, [messages]);

  const componentsById = useMemo(() => {
    const map = new Map<string, A2UIComponent>();
    components.forEach((c) => map.set(c.id, c));
    return map;
  }, [components]);

  const handleValueChange = (pathOrKey: string, newValue: string) => {
    setDataModel((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      const parts = pathOrKey.split('/').filter(Boolean);
      if (parts.length === 0) return next;

      let curr = next;
      for (let i = 0; i < parts.length - 1; i++) {
        if (!curr[parts[i]] || typeof curr[parts[i]] !== 'object') {
          curr[parts[i]] = {};
        }
        curr = curr[parts[i]];
      }
      curr[parts[parts.length - 1]] = newValue;
      return next;
    });
  };

  const handleAction = (action?: any, fallbackText?: string) => {
    if (!action || !action.event) {
      if (fallbackText) onDispatchAction(fallbackText);
      return;
    }

    const { name, payload } = action.event;

    if (name === 'select_stage_option') {
      const selected = payload?.selected_option || fallbackText || 'Selected option';
      onDispatchAction(selected, { event: name, payload });
    } else if (name === 'submit_stage_input') {
      const stage = payload?.stage;
      const customText =
        stage && dataModel.ideation && dataModel.ideation[stage]?.custom_text
          ? dataModel.ideation[stage].custom_text
          : '';
      const text = customText ? customText.trim() : fallbackText || 'Submit answer';
      onDispatchAction(text, { event: name, payload, customText });
    } else if (name === 'export_prd_file') {
      onDispatchAction('Please export the PRD to file.', { event: name, payload });
    } else if (name === 'revise_stage') {
      onDispatchAction('Let us revise the requirements for this stage.', { event: name, payload });
    } else if (name === 'reset_session') {
      onDispatchAction('Start a new project ideation session.', { event: name, payload });
    } else {
      onDispatchAction(fallbackText || name, { event: name, payload });
    }
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(messages, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const rootComp = componentsById.get('root');
  if (components.length === 0) return null;

  return (
    <div className="mt-3.5 bg-slate-900/90 border border-indigo-500/30 rounded-xl p-4 shadow-lg flex flex-col gap-3 text-left">
      {/* Sleek inline surface bar */}
      <div className="flex items-center justify-between text-[11px] pb-2 border-b border-slate-800 text-slate-400">
        <div className="flex items-center gap-1.5 text-indigo-400 font-medium">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Interactive A2UI Widget</span>
          <span className="text-[10px] text-slate-500 font-mono">({surfaceId})</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowJson(!showJson)}
            className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
          >
            <Code2 className="w-3 h-3" />
            {showJson ? 'Hide JSON' : 'JSON'}
          </button>
        </div>
      </div>

      {/* Raw JSON inspection toggle */}
      {showJson && (
        <div className="relative bg-slate-950 p-3 rounded-lg border border-slate-800 text-[11px] font-mono text-indigo-300 max-h-56 overflow-auto">
          <button
            onClick={handleCopyJson}
            className="absolute top-2 right-2 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-slate-300 flex items-center gap-1"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <pre>{JSON.stringify(messages, null, 2)}</pre>
        </div>
      )}

      {/* Interactive Component Tree */}
      <div className="w-full">
        {rootComp ? (
          <A2UIComponentResolver
            componentId="root"
            componentsById={componentsById}
            dataModel={dataModel}
            onValueChange={handleValueChange}
            onAction={handleAction}
            disabled={disabled}
          />
        ) : (
          <div className="flex flex-col gap-2.5">
            {components.map((c) => (
              <A2UIComponentResolver
                key={c.id}
                componentId={c.id}
                componentsById={componentsById}
                dataModel={dataModel}
                onValueChange={handleValueChange}
                onAction={handleAction}
                disabled={disabled}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
