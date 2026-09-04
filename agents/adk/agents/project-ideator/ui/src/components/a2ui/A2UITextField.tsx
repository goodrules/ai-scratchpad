import React from 'react';
import { A2UIComponent } from '../../types/a2ui';

interface A2UITextFieldProps {
  component: A2UIComponent;
  dataModel: Record<string, any>;
  onValueChange: (pathOrKey: string, newValue: string) => void;
  disabled?: boolean;
}

export const A2UITextField: React.FC<A2UITextFieldProps> = ({
  component,
  dataModel,
  onValueChange,
  disabled = false,
}) => {
  const path = typeof component.value === 'object' && component.value?.path
    ? component.value.path
    : component.id;

  // Resolve current value from dataModel path if possible
  const resolveValue = (): string => {
    if (typeof component.value === 'string') return component.value;
    if (typeof component.value === 'object' && component.value?.path) {
      const parts = component.value.path.split('/').filter(Boolean);
      let curr = dataModel;
      for (const p of parts) {
        if (curr && typeof curr === 'object' && p in curr) {
          curr = curr[p];
        } else {
          return '';
        }
      }
      return typeof curr === 'string' ? curr : '';
    }
    return dataModel[component.id] || '';
  };

  const currentValue = resolveValue();

  return (
    <div className="flex flex-col gap-1.5 my-1">
      {component.label && (
        <label className="text-xs font-semibold text-slate-300">
          {component.label}
        </label>
      )}
      <textarea
        rows={2}
        disabled={disabled}
        placeholder={component.placeholder || 'Enter response...'}
        value={currentValue}
        onChange={(e) => onValueChange(path, e.target.value)}
        className="w-full px-3 py-2 text-sm bg-slate-950/80 border border-slate-700/80 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-colors resize-y disabled:opacity-50"
      />
    </div>
  );
};
