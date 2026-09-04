import React from 'react';
import { A2UIComponent } from '../../types/a2ui';
import { A2UIText } from './A2UIText';
import { A2UIButton } from './A2UIButton';
import { A2UITextField } from './A2UITextField';

interface A2UIComponentResolverProps {
  componentId: string;
  componentsById: Map<string, A2UIComponent>;
  dataModel: Record<string, any>;
  onValueChange: (pathOrKey: string, newValue: string) => void;
  onAction: (action?: any, fallbackText?: string) => void;
  disabled?: boolean;
}

export const A2UIComponentResolver: React.FC<A2UIComponentResolverProps> = ({
  componentId,
  componentsById,
  dataModel,
  onValueChange,
  onAction,
  disabled = false,
}) => {
  const comp = componentsById.get(componentId);

  if (!comp) {
    return (
      <div className="text-xs text-amber-500/80 italic p-1 border border-dashed border-amber-500/30 rounded">
        Missing component: {componentId}
      </div>
    );
  }

  switch (comp.component) {
    case 'Column':
      return (
        <div className="flex flex-col gap-3 w-full">
          {comp.children?.map((childId) => (
            <A2UIComponentResolver
              key={childId}
              componentId={childId}
              componentsById={componentsById}
              dataModel={dataModel}
              onValueChange={onValueChange}
              onAction={onAction}
              disabled={disabled}
            />
          ))}
        </div>
      );

    case 'Row':
      return (
        <div className="flex flex-row gap-3 items-center flex-wrap w-full">
          {comp.children?.map((childId) => (
            <A2UIComponentResolver
              key={childId}
              componentId={childId}
              componentsById={componentsById}
              dataModel={dataModel}
              onValueChange={onValueChange}
              onAction={onAction}
              disabled={disabled}
            />
          ))}
        </div>
      );

    case 'Card':
      return (
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 shadow-sm flex flex-col gap-2.5">
          {comp.children?.map((childId) => (
            <A2UIComponentResolver
              key={childId}
              componentId={childId}
              componentsById={componentsById}
              dataModel={dataModel}
              onValueChange={onValueChange}
              onAction={onAction}
              disabled={disabled}
            />
          ))}
        </div>
      );

    case 'Text':
      return <A2UIText component={comp} />;

    case 'Button':
      return (
        <A2UIButton
          component={comp}
          componentsById={componentsById}
          onAction={onAction}
          disabled={disabled}
        />
      );

    case 'TextField':
      return (
        <A2UITextField
          component={comp}
          dataModel={dataModel}
          onValueChange={onValueChange}
          disabled={disabled}
        />
      );

    default:
      return (
        <div className="p-2 border border-slate-700 rounded text-xs text-slate-400">
          Unknown A2UI Component: {comp.component} ({comp.id})
        </div>
      );
  }
};
