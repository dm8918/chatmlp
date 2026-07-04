import type { Conversation } from "../types";
import logo from "../assets/pelambres-logo.png";
import "./Sidebar.css";

interface Props {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  theme,
  onToggleTheme,
}: Props) {
  const isDark = theme === "dark";
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__brand-name">Cerebro</span>
        <img className="sidebar__brand-logo" src={logo} alt="Los Pelambres" />
      </div>

      <button className="sidebar__new" onClick={onNew}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
        </svg>
        Nueva conversación
      </button>

      <div className="sidebar__section-label">Historial</div>

      <nav className="sidebar__history">
        {conversations.map((c) => (
          <button
            key={c.id}
            className={`sidebar__item ${c.id === activeId ? "is-active" : ""}`}
            onClick={() => onSelect(c.id)}
          >
            <span className="sidebar__item-title">{c.title}</span>
            <span className="sidebar__item-time">{c.timestamp}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar__theme">
        <button
          className="theme-switch"
          role="switch"
          aria-checked={isDark}
          aria-label="Cambiar tema claro u oscuro"
          onClick={onToggleTheme}
        >
          <span className="theme-switch__label">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
            </svg>
            Claro
          </span>
          <span className={`theme-switch__track ${isDark ? "is-dark" : ""}`}>
            <span className="theme-switch__thumb" />
          </span>
          <span className="theme-switch__label">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
            </svg>
            Oscuro
          </span>
        </button>
      </div>
    </aside>
  );
}
