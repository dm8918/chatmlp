import type { Message } from "../types";
import StructuredCard from "./StructuredCard";
import "./ChatMessage.css";

export default function ChatMessage({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="msg msg--user">
        <div className="msg__bubble">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="msg msg--assistant">
      {message.type === "structured" ? (
        <StructuredCard data={message.content} />
      ) : (
        <div className="msg__text">{message.content}</div>
      )}
      {message.trace && message.trace.length > 0 && (
        <details className="msg__trace">
          <summary>Ver seguimiento ({message.trace.length} etapas)</summary>
          <pre>{message.trace.join("\n")}</pre>
        </details>
      )}
    </div>
  );
}
