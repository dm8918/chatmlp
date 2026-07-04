import type { Conversation } from "./types";

// Starter state shown on first run (no demo data). A single empty conversation
// ready for the first question. Real saved history takes over after that.
export const seedConversations: Conversation[] = [
  {
    id: "welcome",
    title: "Nueva conversación",
    timestamp: "",
    messages: [],
  },
];
