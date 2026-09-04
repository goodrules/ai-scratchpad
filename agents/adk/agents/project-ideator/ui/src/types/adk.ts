import { A2UIMessage } from './a2ui';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  a2uiMessages?: A2UIMessage[];
}

export interface ADKSession {
  id: string;
  appName: string;
  userId: string;
  state?: Record<string, any>;
  events?: any[];
}
