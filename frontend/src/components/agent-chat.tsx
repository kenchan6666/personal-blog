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
  rewindOwnerAgentConversation,
  stopOwnerAgentTurn,
  syncAgentKnowledge,
  syncAllAgentKnowledge,
  streamOwnerAgent,
  updateAgentKnowledge,
  type AgentConversationSummary,
  type AgentKnowledge,
  type AgentKnowledgeInput,
  type AgentStreamEvent,
  type Localized,
} from "@/lib/api";
import { messagesWithThinking, type ChatMessage } from "@/lib/agent-thinking";
import { CmsModal } from "./cms-modal";
import { MarkdownBody } from "./markdown-body";

export type AgentInsertTarget = keyof Localized | "text";

type Props = {
  compact?: boolean;
  context?: { label: string; value: Localized | string };
  onInsert?: (locale: AgentInsertTarget, text: string) => void;
};

type MobileSheet = "" | "conversations" | "knowledge";

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

const SYNC_ERROR_LABELS: Record<string, string> = {
  embedding_not_configured: "未配置 UNI_API_KEY",
  embedding_unavailable: "Embedding 服务不可用",
  embedding_unauthorized: "UniAPI 密钥无效",
  embedding_model_unavailable:
    "当前 Embedding 模型无可用渠道，已尝试备用模型仍失败",
  embedding_invalid_response: "Embedding 返回格式异常",
  vector_dimension_mismatch: "向量维度不兼容",
  vector_store_rejected: "Qdrant 拒绝写入",
  vector_store_unavailable: "Qdrant 不可用",
};

function syncErrorText(code: string): string {
  return SYNC_ERROR_LABELS[code] ?? "向量同步失败";
}

function pinChangedKnowledge(
  items: AgentKnowledge[],
  changedIds: string[],
): AgentKnowledge[] {
  const wanted = new Set(changedIds);
  return [
    ...items.filter((item) => wanted.has(item.id)),
    ...items.filter((item) => !wanted.has(item.id)),
  ];
}

export function AgentChat({ compact = false, context, onInsert }: Props) {
  const [conversations, setConversations] = useState<
    AgentConversationSummary[]
  >([]);
  const [activeId, setActiveId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [knowledge, setKnowledge] = useState<AgentKnowledge[]>([]);
  const [editingKnowledgeId, setEditingKnowledgeId] = useState<string | null>(
    null,
  );
  const [knowledgeDraft, setKnowledgeDraft] =
    useState<AgentKnowledgeInput>(EMPTY_KNOWLEDGE);
  const [input, setInput] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [sending, setSending] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingKnowledge, setSavingKnowledge] = useState(false);
  const [syncingAllKnowledge, setSyncingAllKnowledge] = useState(false);
  const [syncingKnowledgeIds, setSyncingKnowledgeIds] = useState<Set<string>>(
    new Set(),
  );
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [deletingConversation, setDeletingConversation] = useState(false);
  const [agentActivity, setAgentActivity] = useState("");
  const [toolActivity, setToolActivity] = useState("");
  const [recentKnowledgeIds, setRecentKnowledgeIds] = useState<Set<string>>(
    new Set(),
  );
  const [error, setError] = useState("");
  const [awaitingMore, setAwaitingMore] = useState(false);
  const [mobileSheet, setMobileSheet] = useState<MobileSheet>("");
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const composeRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const knowledgeListRef = useRef<HTMLDivElement>(null);
  const workspaceRef = useRef<HTMLElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const activityTimerRef = useRef<number | null>(null);
  const knowledgeRevealTimerRef = useRef<number | null>(null);

  async function refreshConversations(token: string) {
    const rows = await listAgentConversations(token);
    setConversations(rows);
    return rows;
  }

  async function openConversation(token: string, id: string) {
    const conversation = await getAgentConversation(token, id);
    setActiveId(id);
    setThinking(Boolean(conversation.thinking));
    setMessages(
      messagesWithThinking(conversation.messages, conversation.thinking),
    );
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
    return () => {
      window.clearTimeout(timer);
      if (activityTimerRef.current !== null) {
        window.clearTimeout(activityTimerRef.current);
      }
      if (knowledgeRevealTimerRef.current !== null) {
        window.clearTimeout(knowledgeRevealTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages]);

  useEffect(() => {
    const root = workspaceRef.current;
    const viewport = window.visualViewport;
    if (!root || !viewport) return undefined;
    const sync = () => {
      const inset = Math.max(
        0,
        window.innerHeight - viewport.height - viewport.offsetTop,
      );
      root.style.setProperty("--agent-keyboard-inset", `${inset}px`);
    };
    sync();
    viewport.addEventListener("resize", sync);
    viewport.addEventListener("scroll", sync);
    return () => {
      viewport.removeEventListener("resize", sync);
      viewport.removeEventListener("scroll", sync);
      root.style.removeProperty("--agent-keyboard-inset");
    };
  }, []);

  const latestAssistant = [...messages]
    .reverse()
    .find((item) => item.role === "assistant" && item.content.trim());
  const liveAssistant = [...messages]
    .reverse()
    .find((item) => item.role === "assistant");
  const liveText = Boolean(liveAssistant?.content.trim());
  const awaitingTurn = sending || thinking;
  const isThinking = awaitingTurn && Boolean(liveAssistant) && !liveText;
  const isToolWait = awaitingTurn && liveText && awaitingMore;
  const isStreaming = sending && liveText && !awaitingMore;
  const livePhase = isStreaming
    ? "streaming"
    : isThinking || isToolWait
      ? "thinking"
      : "";

  useEffect(() => {
    if (!awaitingTurn) {
      setAwaitingMore(false);
      return undefined;
    }
    setAwaitingMore(false);
    const timer = window.setTimeout(() => setAwaitingMore(true), 850);
    return () => window.clearTimeout(timer);
  }, [awaitingTurn, liveAssistant?.content]);

  useEffect(() => {
    if (!thinking || sending || !activeId) return undefined;
    const token = getSessionToken();
    if (!token) return undefined;
    let cancelled = false;
    const pull = async () => {
      try {
        const conversation = await getAgentConversation(token, activeId);
        if (cancelled) return;
        setThinking(Boolean(conversation.thinking));
        setMessages(
          messagesWithThinking(conversation.messages, conversation.thinking),
        );
        setConversations((rows) =>
          rows.map((row) =>
            row.id === conversation.id
              ? {
                  ...row,
                  thinking: conversation.thinking,
                  preview: conversation.preview,
                  messageCount: conversation.messageCount,
                  updatedAt: conversation.updatedAt,
                }
              : row,
          ),
        );
        if (!conversation.thinking) {
          const last = conversation.messages[conversation.messages.length - 1];
          if (!last || last.role !== "assistant" || !last.content.trim()) {
            setError("这一轮没有收到完整回复，请再发一次。");
          }
          if (!compact) setKnowledge(await listAgentKnowledge(token));
        }
      } catch {
        /* keep the thinking placeholder until the next poll */
      }
    };
    const timer = window.setInterval(() => void pull(), 2000);
    void pull();
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [thinking, sending, activeId, compact]);

  function handleStreamEvent(event: AgentStreamEvent) {
    if (event.type === "tool_activity") {
      setToolActivity(event.label);
      return;
    }
    if (event.type !== "knowledge_updated") return;
    const pinned = pinChangedKnowledge(event.items, event.changedIds);
    setKnowledge(pinned);
    setRecentKnowledgeIds(new Set());
    const changed = pinned.find((item) => event.changedIds.includes(item.id));
    setAgentActivity(
      changed ? `已同步到“关于我” · ${changed.title}` : "“关于我”已同步",
    );
    if (!compact) setMobileSheet("knowledge");
    if (activityTimerRef.current !== null) {
      window.clearTimeout(activityTimerRef.current);
    }
    if (knowledgeRevealTimerRef.current !== null) {
      window.clearTimeout(knowledgeRevealTimerRef.current);
    }
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.requestAnimationFrame(() => {
      knowledgeListRef.current?.scrollTo({
        top: 0,
        behavior: reduce ? "auto" : "smooth",
      });
    });
    knowledgeRevealTimerRef.current = window.setTimeout(() => {
      setRecentKnowledgeIds(new Set(event.changedIds));
      knowledgeRevealTimerRef.current = null;
    }, reduce ? 0 : 280);
    activityTimerRef.current = window.setTimeout(() => {
      setAgentActivity("");
      setRecentKnowledgeIds(new Set());
      activityTimerRef.current = null;
    }, reduce ? 1200 : 2880);
  }

  async function createConversation() {
    const token = getSessionToken();
    if (!token || sending) return;
    try {
      const row = await createAgentConversation(token);
      await refreshConversations(token);
      await openConversation(token, row.id);
      setMobileSheet("");
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
      setMobileSheet("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法打开对话。");
    } finally {
      setLoading(false);
    }
  }

  async function removeConversation(id: string) {
    const token = getSessionToken();
    if (!token || sending || deletingConversation) return;
    setDeletingConversation(true);
    try {
      await deleteAgentConversation(token, id);
      let rows = await refreshConversations(token);
      if (!rows.length) {
        await createAgentConversation(token);
        rows = await refreshConversations(token);
      }
      if (id === activeId && rows[0]) await openConversation(token, rows[0].id);
      setPendingDeleteId(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法删除对话。");
    } finally {
      setDeletingConversation(false);
    }
  }

  function resizeComposer() {
    const node = composeRef.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = `${Math.min(node.scrollHeight, 160)}px`;
  }

  async function stopTurn() {
    const token = getSessionToken();
    abortRef.current?.abort();
    abortRef.current = null;
    setSending(false);
    setThinking(false);
    setToolActivity("");
    if (!token || !activeId) return;
    try {
      const conversation = await stopOwnerAgentTurn(token, activeId);
      setThinking(Boolean(conversation.thinking));
      setMessages(
        messagesWithThinking(conversation.messages, conversation.thinking),
      );
      await refreshConversations(token);
    } catch {
      /* keep the local stopped state */
    }
  }

  async function send(event?: React.FormEvent, override?: string) {
    event?.preventDefault();
    const text = (override ?? input).trim();
    const token = getSessionToken();
    if ((!text && files.length === 0) || !token || !activeId || sending || thinking)
      return;

    const user: ChatMessage = {
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
    setEditingIndex(null);
    setError("");
    setToolActivity("");
    setThinking(true);
    setSending(true);
    const controller = new AbortController();
    abortRef.current = controller;

    const editorContext = context
      ? [
          `正在编辑：${context.label}`,
          typeof context.value === "string"
            ? `当前内容：${context.value}`
            : `当前三语内容：${JSON.stringify(context.value)}`,
          "除非明确要求写入网站，否则只给建议或可插入正文。",
        ].join("\n")
      : "";

    try {
      const reply = await streamOwnerAgent(
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
        handleStreamEvent,
        controller.signal,
      );
      if (!reply.trim()) {
        throw new Error("这一轮没有收到完整回复，请再发一次。");
      }
      setThinking(false);
      await Promise.all([
        refreshConversations(token),
        compact
          ? Promise.resolve()
          : listAgentKnowledge(token).then(setKnowledge),
      ]);
    } catch (reason) {
      const aborted =
        (reason instanceof DOMException && reason.name === "AbortError") ||
        (reason instanceof Error && reason.name === "AbortError");
      if (aborted) {
        setThinking(false);
        return;
      }
      const busy =
        reason instanceof Error &&
        (reason.message.includes("agent_turn_in_progress") ||
          reason.message.includes("agent_too_many_turns"));
      if (busy) {
        if (reason.message.includes("agent_too_many_turns")) {
          setThinking(false);
          setError("同时进行的对话过多，请稍后再试。");
          setMessages((current) =>
            current.filter(
              (item) => item.id !== assistantId || item.content.trim().length > 0,
            ),
          );
          return;
        }
        setThinking(true);
        try {
          const latest = await getAgentConversation(token, activeId);
          setThinking(Boolean(latest.thinking));
          setMessages(
            messagesWithThinking(latest.messages, latest.thinking),
          );
        } catch {
          /* keep the optimistic thinking bubble */
        }
        return;
      }
      setThinking(false);
      setError(reason instanceof Error ? reason.message : "Agent 暂时无法回应。");
      setMessages((current) =>
        current.filter(
          (item) => item.id !== assistantId || item.content.trim().length > 0,
        ),
      );
    } finally {
      setToolActivity("");
      setSending(false);
      if (abortRef.current === controller) abortRef.current = null;
    }
  }

  async function submitEdit(index: number) {
    const token = getSessionToken();
    const text = editDraft.trim();
    if (!token || !activeId || !text || sending || thinking) return;
    try {
      await rewindOwnerAgentConversation(token, activeId, index, text);
      setMessages((current) => current.slice(0, index));
      setEditingIndex(null);
      await send(undefined, text);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法改写这句话。");
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
      let saved: AgentKnowledge;
      if (editingKnowledgeId) {
        saved = await updateAgentKnowledge(
          token,
          editingKnowledgeId,
          knowledgeDraft,
        );
      } else {
        saved = await createAgentKnowledge(token, knowledgeDraft);
      }
      setKnowledge(await listAgentKnowledge(token));
      setEditingKnowledgeId(null);
      setKnowledgeDraft(EMPTY_KNOWLEDGE);
      if (!saved.vectorSynced) {
        setError(syncErrorText(saved.vectorSyncError));
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法保存资料。");
    } finally {
      setSavingKnowledge(false);
    }
  }

  async function syncKnowledge(id: string) {
    const token = getSessionToken();
    if (!token || syncingAllKnowledge || syncingKnowledgeIds.has(id)) return;
    setError("");
    setSyncingKnowledgeIds((current) => new Set(current).add(id));
    try {
      const synced = await syncAgentKnowledge(token, id);
      setKnowledge((current) =>
        current.map((record) => (record.id === id ? synced : record)),
      );
      if (!synced.vectorSynced) {
        setError(syncErrorText(synced.vectorSyncError));
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "向量同步失败。");
    } finally {
      setSyncingKnowledgeIds((current) => {
        const next = new Set(current);
        next.delete(id);
        return next;
      });
    }
  }

  async function syncAllKnowledge() {
    const token = getSessionToken();
    if (!token || syncingAllKnowledge || syncingKnowledgeIds.size) return;
    setError("");
    setSyncingAllKnowledge(true);
    try {
      const rows = await syncAllAgentKnowledge(token);
      setKnowledge(rows);
      const failed = rows.find((record) => !record.vectorSynced);
      if (failed) {
        setError(syncErrorText(failed.vectorSyncError));
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "批量同步失败。");
    } finally {
      setSyncingAllKnowledge(false);
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
    <section
      ref={workspaceRef}
      className={`agent-workspace${compact ? " is-compact" : ""}${
        mobileSheet ? ` is-${mobileSheet}` : ""
      }`}
    >
      {!compact ? (
        <nav className="agent-mobile-nav" aria-label="Agent 面板">
          {(
            [
              ["conversations", "会话"],
              ["", "对话"],
              ["knowledge", "关于我"],
            ] as const
          ).map(([pane, label]) => (
            <button
              key={label}
              type="button"
              className={mobileSheet === pane ? "is-active" : ""}
              onClick={() =>
                setMobileSheet((current) =>
                  pane === "" ? "" : current === pane ? "" : pane,
                )
              }
            >
              {label}
            </button>
          ))}
        </nav>
      ) : null}
      {!compact ? (
        <button
          type="button"
          className="agent-sheet-backdrop"
          aria-label="关闭"
          onClick={() => setMobileSheet("")}
        />
      ) : null}
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
                  <span>
                    {conversation.thinking
                      ? "思考中…"
                      : conversation.preview || "开始一段新对话"}
                  </span>
                </button>
                <button
                  type="button"
                  className="agent-delete-mini"
                  aria-label="删除对话"
                  onClick={() => setPendingDeleteId(conversation.id)}
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
          <span
            className={`agent-orb${livePhase ? ` is-${livePhase}` : ""}`}
            aria-hidden="true"
          >
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
          </div>
          {awaitingTurn && (livePhase || toolActivity) ? (
            <div
              className={`agent-live-activity is-${livePhase || "thinking"} has-label`}
              aria-live="polite"
              aria-label={
                toolActivity ||
                (isStreaming ? "正在输出" : isToolWait ? "等待工具" : "等待模型")
              }
            >
              <span className="agent-status-bars" aria-hidden="true">
                <i />
                <i />
                <i />
                <i />
              </span>
              <span>
                {toolActivity ||
                  (isStreaming ? "正在输出" : isToolWait ? "等待工具" : "等待模型")}
              </span>
            </div>
          ) : agentActivity ? (
            <div className="agent-live-activity" aria-live="polite">
              <i aria-hidden="true" />
              <span>{agentActivity}</span>
            </div>
          ) : null}
        </div>

        <div
          className={`agent-messages${loading ? " is-transitioning" : ""}`}
          aria-live="polite"
        >
          {loading ? <div className="agent-empty">正在读取对话…</div> : null}
          {messages.map((message, index) => (
            <article
              key={message.id}
              className={`agent-message is-${message.role}${
                awaitingTurn && message.id === liveAssistant?.id
                  ? isStreaming
                    ? " is-streaming"
                    : " is-thinking"
                  : ""
              }`}
              onClick={() => {
                if (message.role !== "user" || awaitingTurn) return;
                if (message.id === "thinking-placeholder") return;
                setEditingIndex(index);
                setEditDraft(message.content);
              }}
            >
              {message.files?.length ? (
                <p className="agent-files">{message.files.join(" · ")}</p>
              ) : null}
              {message.role === "assistant" ? (
                message.content ? (
                  <>
                    <MarkdownBody source={message.content} />
                    {awaitingTurn && message.id === liveAssistant?.id ? (
                      isToolWait ? (
                        <span className="agent-thinking" aria-label="等待工具">
                          <i />
                          <i />
                          <i />
                          <i />
                        </span>
                      ) : (
                        <span className="agent-stream-caret" aria-hidden="true" />
                      )
                    ) : null}
                  </>
                ) : awaitingTurn && message.id === liveAssistant?.id ? (
                  <span className="agent-thinking" aria-label="等待模型">
                    <i />
                    <i />
                    <i />
                    <i />
                  </span>
                ) : null
              ) : editingIndex === index ? (
                <textarea
                  className="agent-message-edit"
                  value={editDraft}
                  autoFocus
                  onClick={(event) => event.stopPropagation()}
                  onChange={(event) => setEditDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      void submitEdit(index);
                    }
                    if (event.key === "Escape") setEditingIndex(null);
                  }}
                  onBlur={() => {
                    if (editDraft.trim() === message.content) {
                      setEditingIndex(null);
                    }
                  }}
                />
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
            {typeof context?.value === "string" ? (
              <button
                type="button"
                className="btn-ghost text-xs"
                disabled={sending}
                onClick={() => onInsert("text", latestAssistant.content)}
              >
                写入此栏
              </button>
            ) : (
              (["zh-Hant", "zh-Hans", "en"] as const).map((locale) => (
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
              ))
            )}
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
              ref={composeRef}
              value={input}
              rows={compact ? 2 : 3}
              disabled={!activeId}
              onChange={(event) => {
                setInput(event.target.value);
                resizeComposer();
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  if (awaitingTurn) return;
                  event.currentTarget.form?.requestSubmit();
                }
              }}
            />
            {awaitingTurn ? (
              <button
                type="button"
                className="agent-send"
                onClick={() => void stopTurn()}
              >
                停止
              </button>
            ) : (
              <button
                type="submit"
                className="agent-send"
                disabled={!activeId || (!input.trim() && files.length === 0)}
              >
                发送
              </button>
            )}
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
            <div className="agent-panel-actions">
              <button
                type="button"
                className="agent-sync-button"
                disabled={
                  syncingAllKnowledge ||
                  syncingKnowledgeIds.size > 0 ||
                  knowledge.length === 0
                }
                onClick={() => void syncAllKnowledge()}
              >
                {syncingAllKnowledge ? "同步中…" : "同步全部"}
              </button>
              <button
                type="button"
                className="agent-new-button"
                onClick={() => editKnowledge()}
              >
                ＋ 添加
              </button>
            </div>
          </div>
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
          <div className="agent-knowledge-list" ref={knowledgeListRef}>
            {knowledge.length === 0 && editingKnowledgeId === null ? (
              <div className="agent-empty">
                还没有个人资料。
              </div>
            ) : null}
            {knowledge.map((record) => {
              const syncing =
                syncingAllKnowledge || syncingKnowledgeIds.has(record.id);
              return (
                <article
                  key={record.id}
                  className={`agent-knowledge-card${
                    recentKnowledgeIds.has(record.id) ? " is-live" : ""
                  }`}
                >
                  <div className="agent-knowledge-meta">
                    <span>{CATEGORY_LABELS[record.category] ?? "其他"}</span>
                    <span
                      className={`agent-vector-status${
                        record.vectorSynced ? " is-synced" : ""
                      }${syncing ? " is-syncing" : ""}`}
                    >
                      <i />
                      {syncing
                        ? "同步中"
                        : record.vectorSynced
                          ? "已同步"
                          : "未同步"}
                    </span>
                  </div>
                  <h3>{record.title}</h3>
                  <p>{record.content}</p>
                  {!record.vectorSynced && record.vectorSyncError && !syncing ? (
                    <p className="agent-sync-error">
                      {syncErrorText(record.vectorSyncError)}
                    </p>
                  ) : null}
                  {record.tags.length ? (
                    <div className="agent-tags">
                      {record.tags.map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))}
                    </div>
                  ) : null}
                  <div className="agent-card-actions">
                    <button
                      type="button"
                      disabled={syncing}
                      onClick={() => void syncKnowledge(record.id)}
                    >
                      {syncing ? "同步中…" : "同步"}
                    </button>
                    <button type="button" onClick={() => editKnowledge(record)}>
                      编辑
                    </button>
                    <button
                      type="button"
                      onClick={() => removeKnowledge(record.id)}
                    >
                      删除
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </aside>
      ) : null}

      <CmsModal
        open={pendingDeleteId !== null}
        title="删除对话？"
        closeLabel="取消删除"
        small
        elevated
        onClose={() => {
          if (!deletingConversation) setPendingDeleteId(null);
        }}
        footer={
          <>
            <button
              type="button"
              className="btn-ghost"
              disabled={deletingConversation}
              onClick={() => setPendingDeleteId(null)}
            >
              取消
            </button>
            <button
              type="button"
              className="agent-danger-button"
              disabled={deletingConversation}
              onClick={() => {
                if (pendingDeleteId) void removeConversation(pendingDeleteId);
              }}
            >
              {deletingConversation ? "删除中…" : "确认删除"}
            </button>
          </>
        }
      >
        <div className="agent-delete-confirm">
          <p>
            将永久删除对话
            <strong>
              “
              {conversations.find((item) => item.id === pendingDeleteId)?.title ??
                "未命名对话"}
              ”
            </strong>
            及其历史消息。
          </p>
          <span>此操作无法撤销。</span>
        </div>
      </CmsModal>
    </section>
  );
}
