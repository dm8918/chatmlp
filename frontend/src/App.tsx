import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import { seedConversations } from "./data";
import { sendChat } from "./api";
import type { Conversation, Message } from "./types";
import "./App.css";

type Theme = "light" | "dark";

const STORAGE_KEY = "cerebro-conversations";
const ACTIVE_KEY = "cerebro-active";
const NEW_TITLE = "Nueva conversación";

function formatTimestamp(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}-${p(d.getMonth() + 1)}-${d.getFullYear()} ${p(
    d.getHours(),
  )}:${p(d.getMinutes())}`;
}

function titleFrom(text: string): string {
  const clean = text.trim().replace(/\s+/g, " ");
  return clean.length > 42 ? `${clean.slice(0, 42).trimEnd()}…` : clean;
}

function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `c-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function sanitizeConversations(raw: unknown): Conversation[] | null {
  if (!Array.isArray(raw)) return null;
  const clean: Conversation[] = [];
  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const c = item as Record<string, unknown>;
    if (typeof c.id !== "string") continue;
    clean.push({
      id: c.id,
      title: typeof c.title === "string" ? c.title : NEW_TITLE,
      timestamp: typeof c.timestamp === "string" ? c.timestamp : formatTimestamp(),
      messages: Array.isArray(c.messages)
        ? (c.messages.filter(
            (m) => m && typeof m === "object" && "role" in m && "type" in m,
          ) as Message[])
        : [],
    });
  }
  return clean;
}

function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const cleaned = sanitizeConversations(JSON.parse(raw));
      if (cleaned && cleaned.length > 0) return cleaned;
      if (cleaned) return []; // valid but empty: respect the user's cleared history
    }
  } catch {
    // corrupt storage: clear it so the app self-heals on next load
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }
  return seedConversations;
}

export default function App() {
  const [conversations, setConversations] =
    useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string>(() => {
    const saved = localStorage.getItem(ACTIVE_KEY);
    const convs = loadConversations();
    if (saved && convs.some((c) => c.id === saved)) return saved;
    return convs[0]?.id ?? "";
  });
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("theme") as Theme) || "light",
  );
  const endRef = useRef<HTMLDivElement>(null);

  const messages = conversations.find((c) => c.id === activeId)?.messages ?? [];

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    localStorage.setItem(ACTIVE_KEY, activeId);
  }, [activeId]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () =>
    setTheme((t) => (t === "light" ? "dark" : "light"));

  const appendToConversation = (id: string, msg: Message) => {
    setConversations((prev) =>
      prev.map((c) =>
        c.id === id
          ? {
              ...c,
              messages: [...(Array.isArray(c.messages) ? c.messages : []), msg],
              timestamp: formatTimestamp(),
            }
          : c,
      ),
    );
  };

  const handleSend = async (text: string) => {
    const userMsg: Message = { role: "user", type: "text", content: text };
    const history = messages;

    let targetId = activeId;
    const existing = conversations.find((c) => c.id === activeId);

    if (existing) {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === targetId
            ? {
                ...c,
                title:
                  c.messages.length === 0 || c.title === NEW_TITLE
                    ? titleFrom(text)
                    : c.title,
                timestamp: formatTimestamp(),
                messages: [...c.messages, userMsg],
              }
            : c,
        ),
      );
    } else {
      targetId = newId();
      const conv: Conversation = {
        id: targetId,
        title: titleFrom(text),
        timestamp: formatTimestamp(),
        messages: [userMsg],
      };
      setConversations((prev) => [conv, ...prev]);
      setActiveId(targetId);
    }

    setLoading(true);
    try {
      const reply = await sendChat([...history, userMsg]);
      appendToConversation(targetId, reply);
    } catch (err) {
      appendToConversation(targetId, {
        role: "assistant",
        type: "text",
        content: `No se pudo obtener respuesta: ${
          err instanceof Error ? err.message : "error desconocido"
        }`,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleNew = () => {
    const empty = conversations.find((c) => c.messages.length === 0);
    if (empty) {
      setActiveId(empty.id);
      return;
    }
    const id = newId();
    const conv: Conversation = {
      id,
      title: NEW_TITLE,
      timestamp: formatTimestamp(),
      messages: [],
    };
    setConversations((prev) => [conv, ...prev]);
    setActiveId(id);
  };

  const handleDelete = (id: string) => {
    setConversations((prev) => {
      const next = prev.filter((c) => c.id !== id);
      if (id === activeId) setActiveId(next[0]?.id ?? "");
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
            {messages.length === 0 && !loading && (
              <div className="chat__empty">
                <h2>¿En qué te ayudo hoy?</h2>
                <p>
                  Escribe una pregunta al asesor de operaciones para comenzar una
                  nueva conversación.
                </p>
              </div>
            )}
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
