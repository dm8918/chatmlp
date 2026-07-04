import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import { conversations as initialConversations, initialMessages } from "./data";
import { sendChat } from "./api";
import type { Conversation, Message } from "./types";
import "./App.css";

type Theme = "light" | "dark";

export default function App() {
  const [conversations, setConversations] =
    useState<Conversation[]>(initialConversations);
  const [activeId, setActiveId] = useState(initialConversations[0].id);
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("theme") as Theme) || "light",
  );
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () =>
    setTheme((t) => (t === "light" ? "dark" : "light"));

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

  const handleDelete = (id: string) => {
    setConversations((prev) => {
      const next = prev.filter((c) => c.id !== id);
      if (id === activeId) {
        setActiveId(next[0]?.id ?? "");
        setMessages([]);
      }
      return next;
    });
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNew}
        onDelete={handleDelete}
        theme={theme}
        onToggleTheme={toggleTheme}
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
