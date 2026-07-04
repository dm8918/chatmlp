import type { Message } from "./types";

export async function sendChat(messages: Message[]): Promise<Message> {
  const payload = messages.map((m) => ({
    role: m.role,
    content: m.type === "text" ? m.content : m.content.title,
  }));

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: payload }),
  });

  if (!res.ok) {
    throw new Error(`Error del servidor: ${res.status}`);
  }

  return (await res.json()) as Message;
}
