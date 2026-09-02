"use client";

import { useEffect, useRef, useState } from "react";
import {
  createAgentConversation,
  createAgentKnowledge,
  deleteAgentConversation,
  deleteAgentKnowledge,
  getAgentConversation,
  getSessionToken,
  listAgentConversations,
  listAgentKnowledge,
  streamOwnerAgent,
  updateAgentKnowledge,
  type AgentConversationSummary,
  type AgentKnowledge,
  type AgentKnowledgeInput,
  type AgentMessage,
  type Localized,
} from "@/lib/api";
import { MarkdownBody } from "./markdown-body";

type Props = {
  compact?: boolean;
  context?: { label: string; value: Localized };
  onInsert?: (locale: keyof Localized, text: string) => void;
};

type DisplayMessage = AgentMessage & { id: string };

const ACTIVE_CONVERSATION_KEY = "portfolio_agent_active_conversation";
const EMPTY_KNOWLEDGE: AgentKnowledgeInput = {
  title: "",
  category: "identity",
  content: "",
  tags: [],
  order: 0,
};

const CATEGORY_LABELS: Record<string, string> = {
  identity: "基本资料",
  experience: "经历",
  education: "教育",
  skills: "技能",
  project: "项目",
  preference: "偏好",
  other: "其他",
};

function messageRows(messages: AgentMessage[]): DisplayMessage[] {
  return messages.map((message, index) => ({
    ...message,
    id: `${message.createdAt}-${index}`,
  }));
}

export function AgentChat({ compact = false, context, onInsert }: Props) {
  const [conversations, setConversations] = useState<
    AgentConversationSummary[]
  >([]);
  const [activeId, setActiveId] = useState("");
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [knowledge, setKnowledge] = useState<AgentKnowledge[]>([]);
  const [editingKnowledgeId, setEditingKnowledgeId] = useState<string | null>(
    null,
  );
  const [knowledgeDraft, setKnowledgeDraft] =
    useState<AgentKnowledgeInput>(EMPTY_KNOWLEDGE);
  const [input, setInput] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingKnowledge, setSavingKnowledge] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  async function refreshConversations(token: string) {
    const rows = await listAgentConversations(token);
    setConversations(rows);
    return rows;
  }

  async function openConversation(token: string, id: string) {
    const conversation = await getAgentConversation(token, id);
    setActiveId(id);
    setMessages(messageRows(conversation.messages));
    window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, id);
  }

  async function initialize() {
    const token = getSessionToken();
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      let rows = await refreshConversations(token);
      if (!rows.length) {
        await createAgentConversation(token);
        rows = await refreshConversations(token);
      }
      const remembered = window.localStorage.getItem(ACTIVE_CONVERSATION_KEY);
      const selected =
        rows.find((row) => row.id === remembered)?.id ?? rows[0]?.id;
      if (selected) await openConversation(token, selected);
      if (!compact) setKnowledge(await listAgentKnowledge(token));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法读取 Agent 数据。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => void initialize(), 0);
    // The workspace is initialized once; tab remounts reload persisted state.
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages]);

  const latestAssistant = [...messages]
    .reverse()
    .find((item) => item.role === "assistant" && item.content.trim());

  async function createConversation() {
    const token = getSessionToken();
    if (!token || sending) return;
    try {
      const row = await createAgentConversation(token);
      await refreshConversations(token);
      await openConversation(token, row.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法新建对话。");
    }
  }

  async function selectConversation(id: string) {
    const token = getSessionToken();
    if (!token || id === activeId || sending) return;
    try {
      setLoading(true);
      await openConversation(token, id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法打开对话。");
    } finally {
      setLoading(false);
    }
  }

  async function removeConversation(id: string) {
    const token = getSessionToken();
    if (!token || sending || !window.confirm("删除这个对话及其历史消息？")) return;
    try {
      await deleteAgentConversation(token, id);
      let rows = await refreshConversations(token);
      if (!rows.length) {
        await createAgentConversation(token);
        rows = await refreshConversations(token);
      }
      if (id === activeId && rows[0]) await openConversation(token, rows[0].id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法删除对话。");
    }
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const text = input.trim();
    const token = getSessionToken();
    if ((!text && files.length === 0) || !token || !activeId || sending) return;

    const user: DisplayMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text || "请分析这些文件。",
      files: files.map((file) => file.name),
      createdAt: new Date().toISOString(),
    };
    const assistantId = crypto.randomUUID();
    const uploads = files;
    setMessages((current) => [
      ...current,
      user,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        files: [],
        createdAt: new Date().toISOString(),
      },
    ]);
    setInput("");
    setFiles([]);
    setError("");
    setSending(true);

    const editorContext = context
      ? [
          `正在编辑：${context.label}`,
          `当前三语内容：${JSON.stringify(context.value)}`,
          "除非明确要求写入网站，否则只给建议或可插入正文。",
        ].join("\n")
      : "";

    try {
      await streamOwnerAgent(
        token,
        activeId,
        user.content,
        editorContext,
        uploads,
        (delta) => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId
                ? { ...item, content: item.content + delta }
                : item,
            ),
          );
        },
      );
      await refreshConversations(token);
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

  function editKnowledge(record?: AgentKnowledge) {
    setEditingKnowledgeId(record?.id ?? "");
    setKnowledgeDraft(
      record
        ? {
            title: record.title,
            category: record.category,
            content: record.content,
            tags: record.tags,
            order: record.order,
          }
        : EMPTY_KNOWLEDGE,
    );
  }

  async function saveKnowledge(event: React.FormEvent) {
    event.preventDefault();
    const token = getSessionToken();
    if (!token || savingKnowledge) return;
    setSavingKnowledge(true);
    setError("");
    try {
      if (editingKnowledgeId) {
        await updateAgentKnowledge(token, editingKnowledgeId, knowledgeDraft);
      } else {
        await createAgentKnowledge(token, knowledgeDraft);
      }
      setKnowledge(await listAgentKnowledge(token));
      setEditingKnowledgeId(null);
      setKnowledgeDraft(EMPTY_KNOWLEDGE);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法保存资料。");
    } finally {
      setSavingKnowledge(false);
    }
  }

  async function removeKnowledge(id: string) {
    const token = getSessionToken();
    if (!token || !window.confirm("从“关于我”知识库删除这项资料？")) return;
    try {
      await deleteAgentKnowledge(token, id);
      setKnowledge(await listAgentKnowledge(token));
      setEditingKnowledgeId(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法删除资料。");
    }
  }

  return (
    <section className={`agent-workspace${compact ? " is-compact" : ""}`}>
      {!compact ? (
        <aside className="agent-conversations">
          <div className="agent-panel-heading">
            <div>
              <span className="eyebrow">CONVERSATIONS</span>
              <h2 className="display-font">对话</h2>
            </div>
            <button
              type="button"
              className="agent-new-button"
              onClick={createConversation}
            >
              ＋ 新对话
            </button>
          </div>
          <div className="agent-conversation-list">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`agent-conversation-item${
                  conversation.id === activeId ? " is-active" : ""
                }`}
              >
                <button
                  type="button"
                  disabled={sending}
                  onClick={() => selectConversation(conversation.id)}
                >
                  <strong>{conversation.title}</strong>
                  <span>{conversation.preview || "开始一段新对话"}</span>
                </button>
                <button
                  type="button"
                  className="agent-delete-mini"
                  aria-label="删除对话"
                  onClick={() => removeConversation(conversation.id)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </aside>
      ) : null}

      <div className="agent-chat">
        <div className="agent-chat-intro">
          <span className="agent-orb" aria-hidden="true">
            <span className="agent-orb-core" />
            <i className="particle p1" />
            <i className="particle p2" />
            <i className="particle p3" />
            <i className="particle p4" />
            <i className="particle p5" />
            <i className="particle p6" />
          </span>
          <div>
            <h2 className="display-font font-bold">
              {context ? `协助编辑 · ${context.label}` : "Portfolio Agent"}
            </h2>
            <p>
              {context
                ? "可询问、改写或生成内容，再逐字写入指定语言。"
                : "会话与消息已持久保存，并会检索右侧个人资料辅助回答。"}
            </p>
          </div>
        </div>

        <div className="agent-messages" aria-live="polite">
          {loading ? <div className="agent-empty">正在读取对话…</div> : null}
          {!loading && messages.length === 0 ? (
            <div className="agent-empty">
              <p>
                {context
                  ? "例如：把这段写得更自然，并给我一个简短版本。"
                  : "问我站内任何内容，或让我创建文章和项目。你也可以在右侧整理个人经历。"}
              </p>
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
                {locale === "zh-Hant"
                  ? "繁中"
                  : locale === "zh-Hans"
                    ? "简中"
                    : "English"}
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
              disabled={sending || !activeId}
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
              disabled={
                sending || !activeId || (!input.trim() && files.length === 0)
              }
            >
              {sending ? "•••" : "发送"}
            </button>
          </div>
        </form>
      </div>

      {!compact ? (
        <aside className="agent-knowledge">
          <div className="agent-panel-heading">
            <div>
              <span className="eyebrow">PERSONAL RAG</span>
              <h2 className="display-font">关于我</h2>
            </div>
            <button
              type="button"
              className="agent-new-button"
              onClick={() => editKnowledge()}
            >
              ＋ 添加
            </button>
          </div>
          <p className="agent-panel-note">
            以模块整理个人资料。绿色标记表示已同步到向量数据库。
          </p>
          {editingKnowledgeId !== null ? (
            <form className="agent-knowledge-form" onSubmit={saveKnowledge}>
              <input
                required
                value={knowledgeDraft.title}
                placeholder="标题，例如：我的工作经历"
                onChange={(event) =>
                  setKnowledgeDraft((current) => ({
                    ...current,
                    title: event.target.value,
                  }))
                }
              />
              <select
                value={knowledgeDraft.category}
                onChange={(event) =>
                  setKnowledgeDraft((current) => ({
                    ...current,
                    category: event.target.value,
                  }))
                }
              >
                {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              <textarea
                required
                rows={8}
                value={knowledgeDraft.content}
                placeholder="使用清晰的自然语言记录事实、经历、偏好或背景…"
                onChange={(event) =>
                  setKnowledgeDraft((current) => ({
                    ...current,
                    content: event.target.value,
                  }))
                }
              />
              <input
                value={knowledgeDraft.tags.join(", ")}
                placeholder="标签，用逗号分隔"
                onChange={(event) =>
                  setKnowledgeDraft((current) => ({
                    ...current,
                    tags: event.target.value
                      .split(/[,，]/)
                      .map((tag) => tag.trim())
                      .filter(Boolean),
                  }))
                }
              />
              <div className="agent-form-actions">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => setEditingKnowledgeId(null)}
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={savingKnowledge}
                >
                  {savingKnowledge ? "保存中…" : "保存并同步"}
                </button>
              </div>
            </form>
          ) : null}
          <div className="agent-knowledge-list">
            {knowledge.length === 0 && editingKnowledgeId === null ? (
              <div className="agent-empty">
                还没有个人资料。添加后，Agent 会按问题检索相关内容。
              </div>
            ) : null}
            {knowledge.map((record) => (
              <article key={record.id} className="agent-knowledge-card">
                <div className="agent-knowledge-meta">
                  <span>{CATEGORY_LABELS[record.category] ?? "其他"}</span>
                  <i
                    className={record.vectorSynced ? "is-synced" : ""}
                    title={
                      record.vectorSynced ? "向量已同步" : "向量未同步，将使用文本检索"
                    }
                  />
                </div>
                <h3>{record.title}</h3>
                <p>{record.content}</p>
                {record.tags.length ? (
                  <div className="agent-tags">
                    {record.tags.map((tag) => <span key={tag}>{tag}</span>)}
                  </div>
                ) : null}
                <div className="agent-card-actions">
                  <button type="button" onClick={() => editKnowledge(record)}>
                    编辑
                  </button>
                  <button type="button" onClick={() => removeKnowledge(record.id)}>
                    删除
                  </button>
                </div>
              </article>
            ))}
          </div>
        </aside>
      ) : null}
    </section>
  );
}
