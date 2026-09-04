import React from 'react';
import { A2UIComponent } from '../../types/a2ui';

interface A2UIButtonProps {
  component: A2UIComponent;
  componentsById: Map<string, A2UIComponent>;
  onAction: (action?: any, fallbackText?: string) => void;
  disabled?: boolean;
}

export const A2UIButton: React.FC<A2UIButtonProps> = ({
  component,
  componentsById,
  onAction,
  disabled = false,
}) => {
  // Determine child label text
  let labelText = component.text || '';
  if (component.child && componentsById.has(component.child)) {
    labelText = componentsById.get(component.child)?.text || component.child;
  }

  const variant = component.variant || 'outlined';

  let variantClasses = 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700';
  if (variant === 'primary') {
    variantClasses =
      'bg-indigo-600 hover:bg-indigo-500 text-white font-medium shadow-md shadow-indigo-950 border-indigo-500 hover:shadow-indigo-500/20';
  } else if (variant === 'filled') {
    variantClasses =
      'bg-emerald-600 hover:bg-emerald-500 text-white font-medium shadow-md shadow-emerald-950 border-emerald-500 hover:shadow-emerald-500/20';
  } else if (variant === 'outlined') {
    variantClasses =
      'bg-slate-800/80 hover:bg-slate-700 text-slate-200 border-slate-700/80 hover:border-slate-500';
  }

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onAction(component.action, labelText)}
      className={`px-4 py-2.5 rounded-lg border text-sm transition-all duration-150 text-left flex items-center justify-between group disabled:opacity-50 disabled:cursor-not-allowed ${variantClasses}`}
    >
      <span className="font-medium">{labelText}</span>
      <span className="ml-2 text-xs opacity-60 group-hover:opacity-100 transition-opacity">
        →
      </span>
    </button>
  );
};
