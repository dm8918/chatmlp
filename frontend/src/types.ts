export interface TableData {
  columns: string[];
  rows: string[][];
}

export interface StructuredContent {
  badge?: string;
  title: string;
  subtitle?: string;
  table?: TableData;
}

export type Message =
  | { role: "user"; type: "text"; content: string }
  | { role: "assistant"; type: "text"; content: string; trace?: string[] }
  | {
      role: "assistant";
      type: "structured";
      content: StructuredContent;
      trace?: string[];
    };

export interface Conversation {
  id: string;
  title: string;
  timestamp: string;
  messages: Message[];
}
