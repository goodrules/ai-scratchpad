import React from 'react';
import { A2UIComponent } from '../../types/a2ui';

interface A2UITextProps {
  component: A2UIComponent;
}

export const A2UIText: React.FC<A2UITextProps> = ({ component }) => {
  const text = component.text || '';
  const variant = component.variant || 'body1';

  switch (variant) {
    case 'h1':
      return <h1 className="text-2xl font-bold text-white tracking-tight mb-2">{text}</h1>;
    case 'h2':
      return <h2 className="text-xl font-semibold text-slate-100 tracking-tight mb-1">{text}</h2>;
    case 'h3':
      return <h3 className="text-lg font-medium text-slate-200 mb-1">{text}</h3>;
    case 'subtitle1':
      return <h4 className="text-base font-medium text-indigo-300">{text}</h4>;
    case 'subtitle2':
      return <h4 className="text-sm font-medium text-indigo-400 uppercase tracking-wider">{text}</h4>;
    case 'caption':
      return (
        <span className="inline-block text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-950/70 text-indigo-400 border border-indigo-800/50 mb-1">
          {text}
        </span>
      );
    case 'body2':
      return (
        <div className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed bg-slate-900/60 p-3 rounded-lg border border-slate-800 font-mono">
          {text}
        </div>
      );
    case 'body1':
    default:
      return <p className="text-sm text-slate-300 leading-relaxed">{text}</p>;
  }
};
