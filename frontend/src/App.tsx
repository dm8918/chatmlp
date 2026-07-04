import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import { conversations, initialMessages } from "./data";
import { sendChat } from "./api";
import type { Message } from "./types";
import "./App.css";

export default function App() {
  const [activeId, setActiveId] = useState(conversations[0].id);
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (text: string) => {
    const userMsg: Message = { role: "user", type: "text", content: text };
    const next = [...messages, userMsg];
    setMessages(next);
    setLoading(true);
    try {
      const reply = await sendChat(next);
      setMessages((prev) => [...prev, reply]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          type: "text",
          content: `No se pudo obtener respuesta: ${
            err instanceof Error ? err.message : "error desconocido"
          }`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleNew = () => {
    setMessages([]);
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNew}
      />

      <main className="chat">
        <div className="chat__scroll">
          <div className="chat__inner">
            {messages.map((m, i) => (
              <ChatMessage key={i} message={m} />
            ))}
            {loading && (
              <div className="chat__typing">El asesor está escribiendo…</div>
            )}
            <div ref={endRef} />
          </div>
        </div>

        <div className="chat__composer">
          <div className="chat__inner">
            <ChatInput onSend={handleSend} disabled={loading} />
          </div>
        </div>
      </main>
    </div>
  );
}
