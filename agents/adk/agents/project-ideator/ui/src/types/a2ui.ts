export type A2UIComponentType =
  | 'Column'
  | 'Row'
  | 'Text'
  | 'Button'
  | 'TextField'
  | 'Card'
  | 'RadioGroup';

export interface A2UIAction {
  event?: {
    name: string;
    payload?: Record<string, any>;
  };
}

export interface A2UIComponent {
  id: string;
  component: A2UIComponentType | string;
  variant?: string;
  text?: string;
  label?: string;
  placeholder?: string;
  children?: string[];
  child?: string;
  value?: { path?: string } | string;
  action?: A2UIAction;
  [key: string]: any;
}

export interface CreateSurfaceMessage {
  surfaceId: string;
  catalogId?: string;
}

export interface UpdateComponentsMessage {
  surfaceId: string;
  components: A2UIComponent[];
}

export interface UpdateDataModelMessage {
  surfaceId: string;
  path?: string;
  value?: any;
}

export interface A2UIMessage {
  version?: string;
  createSurface?: CreateSurfaceMessage;
  beginRendering?: CreateSurfaceMessage;
  updateComponents?: UpdateComponentsMessage;
  surfaceUpdate?: UpdateComponentsMessage;
  updateDataModel?: UpdateDataModelMessage;
  dataModelUpdate?: UpdateDataModelMessage;
}
