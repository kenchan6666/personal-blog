import type { AgentMessage } from "./api";

export type ChatMessage = AgentMessage & { id: string };

export function messageRows(messages: AgentMessage[]): ChatMessage[] {
  return messages.map((message, index) => ({
    ...message,
    id: `${message.createdAt}-${index}`,
  }));
}

export function messagesWithThinking(
  messages: AgentMessage[],
  thinking?: boolean,
): ChatMessage[] {
  const rows = messageRows(messages);
  if (!thinking) return rows;
  const last = rows[rows.length - 1];
  if (!last || last.role === "assistant") return rows;
  return [
    ...rows,
    {
      id: "thinking-placeholder",
      role: "assistant",
      content: "",
      files: [],
      createdAt: last.createdAt,
    },
  ];
}
