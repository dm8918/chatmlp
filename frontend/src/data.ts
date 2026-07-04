import type { Conversation, Message } from "./types";

export const conversations: Conversation[] = [
  { id: "1", title: "cual es la utilizacion CAEX del día 5 de junio", timestamp: "02-07-2026 14:22" },
  { id: "2", title: "dime las perdidas de la última semana", timestamp: "02-07-2026 12:02" },
  { id: "3", title: "dime que pasó el 4 de junio 2026", timestamp: "02-07-2026 11:57" },
  { id: "4", title: "cuales son los focos del plan de jornada", timestamp: "02-07-2026 11:53" },
  { id: "5", title: "revisa el chat de Chat de coordinación", timestamp: "02-07-2026 11:47" },
  { id: "6", title: "cuál es la utilización promedio del turno", timestamp: "02-07-2026 11:43" },
  { id: "7", title: "soy gerente general, dame un resumen", timestamp: "02-07-2026 11:47" },
  { id: "8", title: "cuál es la utilización promedio del mes", timestamp: "02-07-2026 11:43" },
  { id: "9", title: "soy gerente general, dame un resumen", timestamp: "02-07-2026 11:40" },
];

export const initialMessages: Message[] = [
  {
    role: "user",
    type: "text",
    content: "cual es la utilizacion CAEX del día 5 de junio, apertúrala por CAEX",
  },
  {
    role: "assistant",
    type: "structured",
    content: {
      badge: "Datos estructurados + Asesor de operaciones",
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
