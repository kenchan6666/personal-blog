"use client";

import { useEffect, useRef, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import {
  streamPublicGuide,
  type PublicGuideMessage,
} from "@/lib/api";
import {
  nextTypedText,
  typewriterDelayMs,
} from "@/lib/guide-typewriter";
import { MarkdownBody } from "./markdown-body";

type Props = {
  locale: Locale;
  dict: Dictionary["guide"];
  open: boolean;
  onClose: () => void;
};

type DisplayMessage = PublicGuideMessage & { id: string };

function useGuideTypewriter(target: string) {
  const [shown, setShown] = useState("");
  const [reduce, setReduce] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduce(mq.matches);
    const frame = window.requestAnimationFrame(sync);
    mq.addEventListener("change", sync);
    return () => {
      window.cancelAnimationFrame(frame);
      mq.removeEventListener("change", sync);
    };
  }, []);

  const from = target.startsWith(shown) ? shown : "";
  const text = reduce ? target : from;
  const typing = !reduce && Boolean(target) && text !== target;

  useEffect(() => {
    if (!typing) return undefined;
    const timer = window.setTimeout(() => {
      setShown(nextTypedText(from, target));
    }, typewriterDelayMs(from, target));
    return () => window.clearTimeout(timer);
  }, [from, target, typing]);

  return { text, typing };
}

function errorText(code: string, dict: Dictionary["guide"]): string {
  if (code === "public_agent_busy") {
    return dict.busy;
  }
  if (
    code === "public_agent_rate_limited" ||
    code === "public_agent_request_in_progress"
  ) {
    return dict.rateLimited;
  }
  if (code === "public_agent_daily_budget_reached") {
    return dict.dailyLimit;
  }
  return dict.unavailable;
}

export function PublicGuide({ locale, dict, open, onClose }: Props) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [idleSince, setIdleSince] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const liveAssistant = [...messages]
    .reverse()
    .find((item) => item.role === "assistant");
  const { text: typed, typing } = useGuideTypewriter(
    liveAssistant?.content ?? "",
  );
  const liveText = Boolean(typed.trim());
  const awaitingTurn = sending || typing;
  const gapKey = `${sending ? "1" : "0"}:${typed}`;
  const awaitingMore = idleSince === gapKey && awaitingTurn && !typing;
  const isThinking = awaitingTurn && Boolean(liveAssistant) && !typed.trim();
  const isToolWait = sending && liveText && awaitingMore;
  const isStreaming = awaitingTurn && liveText && !awaitingMore;
  const livePhase = isStreaming
    ? "streaming"
    : isThinking || isToolWait
      ? "thinking"
      : "";

  useEffect(() => {
    if (!sending && !typing) return undefined;
    const timer = window.setTimeout(() => setIdleSince(gapKey), 850);
    return () => window.clearTimeout(timer);
  }, [gapKey, sending, typing]);

  useEffect(() => {
    if (!open) return;
    const frame = window.requestAnimationFrame(() => inputRef.current?.focus());
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => {
      window.cancelAnimationFrame(frame);
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose, open]);

  useEffect(() => {
    endRef.current?.scrollIntoView({
      behavior: typing ? "auto" : "smooth",
      block: "nearest",
    });
  }, [messages, typed, typing]);

  async function ask(question: string) {
    const text = question.trim();
    if (!text || sending || typing) return;
    const history: PublicGuideMessage[] = messages
      .filter((message) => message.content.trim())
      .map(({ role, content }) => ({ role, content }))
      .slice(-6);
    const userId = crypto.randomUUID();
    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      { id: userId, role: "user", content: text },
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setInput("");
    setError("");
    setSending(true);
    try {
      await streamPublicGuide(locale, text, history, (delta) => {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? { ...message, content: message.content + delta }
              : message,
          ),
        );
      });
    } catch (reason) {
      const code = reason instanceof Error ? reason.message : "";
      setError(errorText(code, dict));
      setMessages((current) =>
        current.filter(
          (message) =>
            message.id !== assistantId || message.content.trim().length > 0,
        ),
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <div
      className={`public-guide${open ? " is-open" : ""}`}
      aria-hidden={!open}
    >
      <button
        type="button"
        className="public-guide-scrim"
        aria-label={dict.close}
        tabIndex={open ? 0 : -1}
        onClick={onClose}
      />
      <section
        className="public-guide-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="public-guide-title"
      >
        <header className="public-guide-header">
          <span
            className={`guide-orb${livePhase ? ` is-${livePhase}` : ""}`}
            aria-hidden="true"
          >
            <i />
            <i />
            <i />
          </span>
          <div>
            <span className="eyebrow">{dict.eyebrow}</span>
            <h2 id="public-guide-title" className="display-font">
              {dict.title}
            </h2>
          </div>
          <button
            type="button"
            className="icon-btn"
            aria-label={dict.close}
            onClick={onClose}
          >
            {'\u00d7'}
          </button>
        </header>

        <div className="public-guide-messages" aria-live="polite">
          {messages.length === 0 ? (
            <div className="public-guide-welcome">
              <p>{dict.intro}</p>
              <div className="public-guide-prompts">
                {dict.prompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    disabled={awaitingTurn}
                    onClick={() => void ask(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
          {messages.map((message) => {
            const live = message.id === liveAssistant?.id;
            const source =
              live && message.role === "assistant" ? typed : message.content;
            return (
              <article
                key={message.id}
                className={`public-guide-message is-${message.role}${
                  awaitingTurn && live
                    ? isStreaming
                      ? " is-streaming"
                      : " is-thinking"
                    : ""
                }`}
              >
                {message.role === "assistant" ? (
                  source ? (
                    <>
                      <MarkdownBody source={source} />
                      {awaitingTurn && live ? (
                        isToolWait ? (
                          <span
                            className="agent-thinking"
                            aria-label={dict.thinking}
                          >
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
                  ) : (
                    <span className="agent-thinking" aria-label={dict.waitingModel}>
                      <i />
                      <i />
                      <i />
                      <i />
                    </span>
                  )
                ) : (
                  <p>{message.content}</p>
                )}
              </article>
            );
          })}
          <div ref={endRef} />
        </div>

        <form
          className="public-guide-composer"
          onSubmit={(event) => {
            event.preventDefault();
            void ask(input);
          }}
        >
          {error ? <p className="public-guide-error">{error}</p> : null}
          <div>
            <textarea
              ref={inputRef}
              rows={2}
              maxLength={400}
              value={input}
              disabled={awaitingTurn}
              placeholder={dict.placeholder}
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
              disabled={awaitingTurn || !input.trim()}
              aria-label={dict.send}
            >
              {awaitingTurn ? "..." : dict.send}
            </button>
          </div>
          <p>{dict.privacy}</p>
        </form>
      </section>
    </div>
  );
}
