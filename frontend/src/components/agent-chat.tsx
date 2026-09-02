"use client";

import { useEffect, useRef, useState } from "react";
import { getSessionToken, streamOwnerAgent, type Localized } from "@/lib/api";
import { MarkdownBody } from "./markdown-body";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  files?: string[];
};

type Props = {
  compact?: boolean;
  context?: { label: string; value: Localized };
  onInsert?: (locale: keyof Localized, text: string) => void;
};

export function AgentChat({ compact = false, context, onInsert }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages]);

  const latestAssistant = [...messages]
    .reverse()
    .find((item) => item.role === "assistant" && item.content.trim());

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const text = input.trim();
    const token = getSessionToken();
    if ((!text && files.length === 0) || !token || sending) return;

    const user: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text || "请分析这些文件。",
      files: files.map((file) => file.name),
    };
    const assistantId = crypto.randomUUID();
    const uploads = files;
    setMessages((current) => [
      ...current,
      user,
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setInput("");
    setFiles([]);
    setError("");
    setSending(true);

    const contextualMessage = context
      ? [
          `我正在编辑「${context.label}」。以下是当前三语内容：`,
          JSON.stringify(context.value),
          "请结合这个编辑上下文回答。除非我明确要求写入网站，否则只给建议或可插入的正文。",
          "",
          user.content,
        ].join("\n")
      : user.content;

    try {
      await streamOwnerAgent(token, contextualMessage, uploads, (delta) => {
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId
              ? { ...item, content: item.content + delta }
              : item,
          ),
        );
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Agent 暂时无法回应。");
      setMessages((current) =>
        current.filter(
          (item) => item.id !== assistantId || item.content.trim().length > 0,
        ),
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <section className={`agent-chat${compact ? " is-compact" : ""}`}>
      <div className="agent-chat-intro">
        <span className="agent-orb" aria-hidden="true">✦</span>
        <div>
          <h2 className="display-font font-bold">
            {context ? `协助编辑 · ${context.label}` : "Portfolio Agent"}
          </h2>
          <p>
            {context
              ? "可询问、改写或生成内容，再逐字写入指定语言。"
              : "了解你的简介、项目、文章、日志和评论，也能创建 Draft 内容。"}
          </p>
        </div>
      </div>

      <div className="agent-messages" aria-live="polite">
        {messages.length === 0 ? (
          <div className="agent-empty">
            <p>{context ? "例如：把这段写得更自然，并给我一个简短版本。" : "问我站内任何内容，或让我创建一篇文章、一个项目。新内容会先保存为 Draft。"}</p>
          </div>
        ) : null}
        {messages.map((message) => (
          <article
            key={message.id}
            className={`agent-message is-${message.role}`}
          >
            {message.files?.length ? (
              <p className="agent-files">{message.files.join(" · ")}</p>
            ) : null}
            {message.role === "assistant" ? (
              message.content ? (
                <MarkdownBody source={message.content} />
              ) : (
                <span className="agent-thinking">正在思考</span>
              )
            ) : (
              <p className="whitespace-pre-wrap">{message.content}</p>
            )}
          </article>
        ))}
        <div ref={endRef} />
      </div>

      {onInsert && latestAssistant ? (
        <div className="agent-insert-row">
          <span>逐字写入：</span>
          {(["zh-Hant", "zh-Hans", "en"] as const).map((locale) => (
            <button
              key={locale}
              type="button"
              className="btn-ghost text-xs"
              disabled={sending}
              onClick={() => onInsert(locale, latestAssistant.content)}
            >
              {locale === "zh-Hant" ? "繁中" : locale === "zh-Hans" ? "简中" : "English"}
            </button>
          ))}
        </div>
      ) : null}

      {error ? <p className="agent-error">{error}</p> : null}
      <form className="agent-composer" onSubmit={send}>
        {files.length ? (
          <div className="agent-upload-list">
            {files.map((file) => (
              <span key={`${file.name}-${file.size}`}>{file.name}</span>
            ))}
          </div>
        ) : null}
        <div className="agent-compose-row">
          <button
            type="button"
            className="icon-btn"
            aria-label="上传文件或图片"
            onClick={() => fileRef.current?.click()}
          >
            ＋
          </button>
          <input
            ref={fileRef}
            className="sr-only"
            type="file"
            multiple
            accept="image/*,.pdf,.txt,.md,.doc,.docx,.csv,.xlsx,.ppt,.pptx"
            onChange={(event) =>
              setFiles(Array.from(event.target.files ?? []).slice(0, 5))
            }
          />
          <textarea
            value={input}
            rows={compact ? 2 : 3}
            placeholder="输入消息…"
            disabled={sending}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <button
            type="submit"
            className="agent-send"
            disabled={sending || (!input.trim() && files.length === 0)}
          >
            {sending ? "•••" : "发送"}
          </button>
        </div>
      </form>
    </section>
  );
}
