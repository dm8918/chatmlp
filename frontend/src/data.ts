import type { Conversation, Message } from "./types";

const demoMessages: Message[] = [
  {
    role: "user",
    type: "text",
    content: "cual es la utilizacion CAEX del día 5 de junio, apertúrala por CAEX",
  },
  {
    role: "assistant",
    type: "structured",
    content: {
      title: "Utilización CAEX – Flota productiva | 5 de junio de 2026",
      subtitle: "Utilización global de flota productiva: 86,1%",
      table: {
        columns: ["CAEX", "Utilización"],
        rows: [
          ["EX324", "98,0%"],
          ["EX371", "97,4%"],
          ["EX363", "96,7%"],
          ["EX364", "92,5%"],
          ["CA101", "91,6%"],
          ["CA111", "90,7%"],
        ],
      },
    },
  },
];

// Seed shown on first run only. After that, real saved history takes over.
export const seedConversations: Conversation[] = [
  {
    id: "seed-1",
    title: "cual es la utilizacion CAEX del día 5 de junio",
    timestamp: "02-07-2026 14:22",
    messages: demoMessages,
  },
];
