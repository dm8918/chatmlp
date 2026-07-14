import { useRef, useState } from "react";
import type { Message } from "../types";
import StructuredCard from "./StructuredCard";
import Markdown from "./Markdown";
import { downloadMessagePdf } from "../pdf";
import "./ChatMessage.css";

export default function ChatMessage({ message }: { message: Message }) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(false);

  if (message.role === "user") {
    return (
      <div className="msg msg--user">
        <div className="msg__bubble">{message.content}</div>
      </div>
    );
  }

  const isError = message.type === "text" && message.isError === true;
  const canDownload = !isError;

  const handleDownload = async () => {
    if (!contentRef.current || exporting) return;
    setExporting(true);
    setExportError(false);
    try {
      await downloadMessagePdf(contentRef.current);
    } catch (err) {
      console.error("No se pudo generar el PDF:", err);
      setExportError(true);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="msg msg--assistant">
      {message.type === "structured" ? (
        <div ref={contentRef}>
          <StructuredCard data={message.content} />
        </div>
      ) : (
        <div
          ref={contentRef}
          className={"msg__text" + (isError ? " msg__text--error" : "")}
        >
          {isError ? (
            message.content
          ) : (
            <Markdown>{message.content}</Markdown>
          )}
        </div>
      )}

      <div className="msg__actions">
        {canDownload && (
          <button
            type="button"
            className="msg__pdf-btn"
            onClick={handleDownload}
            disabled={exporting}
            title="Descargar esta respuesta como PDF"
          >
            {exporting ? "Generando PDF…" : "⬇ Descargar PDF"}
          </button>
        )}
        {exportError && (
          <span className="msg__pdf-error">
            No se pudo generar el PDF. Inténtalo de nuevo.
          </span>
        )}
        {message.trace && message.trace.length > 0 && (
          <details className="msg__trace">
            <summary>Ver seguimiento ({message.trace.length} etapas)</summary>
            <ol className="msg__trace-steps">
              {message.trace.map((step, i) => (
                <li key={i}>
                  <pre>{step}</pre>
                </li>
              ))}
            </ol>
          </details>
        )}
      </div>
    </div>
  );
}
