import type { Conversation } from "../types";
import logo from "../assets/pelambres-logo.png";
import "./Sidebar.css";

interface Props {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export default function Sidebar({ conversations, activeId, onSelect, onNew }: Props) {
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

      <div className="sidebar__profile">
        <span className="sidebar__avatar">NT</span>
        <span className="sidebar__profile-info">
          <span className="sidebar__profile-name">Nico Tagle</span>
          <span className="sidebar__profile-role">Administrador</span>
        </span>
      </div>
    </aside>
  );
}
