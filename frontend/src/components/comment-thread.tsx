"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  fetchPublicComments,
  submitPublicComment,
  type PublicComment,
} from "@/lib/api";
import { SoftLoader } from "./page-loading";

type Props = {
  kind: "articles" | "journals";
  slug: string;
  dict: Dictionary;
};

export function CommentThread({ kind, slug, dict }: Props) {
  const labels = dict.comments;
  const [comments, setComments] = useState<PublicComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [body, setBody] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(false);
    void fetchPublicComments(kind, slug)
      .then((next) => {
        if (!cancelled) setComments(next);
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [kind, slug]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    setMessage(null);
    setError(null);
    try {
      await submitPublicComment(kind, slug, { displayName, email, body });
      setDisplayName("");
      setEmail("");
      setBody("");
      setMessage(labels.submitted);
      setSubmitted(true);
    } catch {
      setError(labels.error);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="comment-thread">
      <h2 className="comment-thread-title display-font">{labels.title}</h2>
      {loading ? (
        <div className="mb-8">
          <SoftLoader label={dict.loadingPage} />
        </div>
      ) : loadError ? (
        <p className="mb-8 text-sm text-[var(--danger)]">{dict.errorPage}</p>
      ) : comments.length === 0 ? (
        <p className="mb-8 text-sm text-[var(--text-muted)]">{labels.empty}</p>
      ) : (
        <ul className="comment-list">
          {comments.map((comment) => (
            <li key={comment.id} className="comment-card glass">
              <p className="comment-name">{comment.displayName}</p>
              <p className="comment-body">{comment.body}</p>
              {comment.ownerReply ? (
                <p className="comment-owner">
                  <span className="comment-owner-label">{labels.ownerReply}</span>
                  {` ${comment.ownerReply}`}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {submitted ? (
        <p className="comment-status is-ok">{message}</p>
      ) : (
        <form onSubmit={onSubmit} className="comment-form glass">
          <div className="comment-row">
            <label className="comment-field">
              {labels.name}
              <input
                className="field"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                autoComplete="nickname"
                required
              />
            </label>
            <label className="comment-field">
              {labels.email}
              <input
                type="email"
                className="field"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>
          </div>
          <label className="comment-field mb-4">
            {labels.body}
            <textarea
              className="field"
              rows={4}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
            />
          </label>
          {error ? <p className="comment-status is-err">{error}</p> : null}
          <button type="submit" className="btn-cta" disabled={sending}>
            {sending ? labels.sending : labels.submit}
          </button>
        </form>
      )}
    </section>
  );
}
