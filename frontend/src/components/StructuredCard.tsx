import type { StructuredContent } from "../types";
import "./StructuredCard.css";

export default function StructuredCard({ data }: { data: StructuredContent }) {
  return (
    <div className="card">
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
