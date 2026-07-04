import type { StructuredContent } from "../types";
import "./StructuredCard.css";

export default function StructuredCard({ data }: { data: StructuredContent }) {
  return (
    <div className="card">
      {data.badge && (
        <span className="card__badge">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18" />
            <rect x="7" y="10" width="3" height="7" />
            <rect x="12" y="6" width="3" height="11" />
            <rect x="17" y="13" width="3" height="4" />
          </svg>
          {data.badge}
        </span>
      )}

      <h2 className="card__title">{data.title}</h2>
      {data.subtitle && <p className="card__subtitle">{data.subtitle}</p>}

      {data.table && (
        <table className="card__table">
          <thead>
            <tr>
              {data.table.columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.table.rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
