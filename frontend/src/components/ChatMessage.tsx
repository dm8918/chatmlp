import type { Message } from "../types";
import StructuredCard from "./StructuredCard";
import Markdown from "./Markdown";
import "./ChatMessage.css";

export default function ChatMessage({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="msg msg--user">
        <div className="msg__bubble">{message.content}</div>
      </div>
    );
  }

  const isError = message.type === "text" && message.isError === true;

  return (
    <div className="msg msg--assistant">
      {message.type === "structured" ? (
        <StructuredCard data={message.content} />
      ) : (
        <div className={"msg__text" + (isError ? " msg__text--error" : "")}>
          {isError ? (
            message.content
          ) : (
            <Markdown>{message.content}</Markdown>
          )}
        </div>
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
  );
}
