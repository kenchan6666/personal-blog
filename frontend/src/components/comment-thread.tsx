"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import {
  fetchPublicComments,
  submitPublicComment,
  type PublicComment,
} from "@/lib/api";

type Props = {
  kind: "articles" | "journals";
  slug: string;
  dict: Dictionary;
};

export function CommentThread({ kind, slug, dict }: Props) {
  const labels = dict.comments;
  const [comments, setComments] = useState<PublicComment[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [body, setBody] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    void fetchPublicComments(kind, slug).then(setComments);
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
    } catch {
      setError(labels.error);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="mt-14 max-w-3xl">
      <h2 className="display-font mb-6 text-2xl font-bold">{labels.title}</h2>
      {comments.length === 0 ? (
        <p className="mb-8 text-sm text-[var(--text-muted)]">{labels.empty}</p>
      ) : (
        <ul className="mb-8 space-y-5">
          {comments.map((comment) => (
            <li
              key={comment.id}
              className="glass rounded-[var(--radius-card)] p-4"
            >
              <p className="text-sm font-semibold">{comment.displayName}</p>
              <p className="mt-2 whitespace-pre-wrap text-[var(--text-primary)]">
                {comment.body}
              </p>
              {comment.ownerReply ? (
                <p className="mt-3 border-t border-white/10 pt-3 text-sm text-[var(--text-muted)]">
                  <span className="font-semibold text-[var(--accent-link)]">
                    {labels.ownerReply}
                  </span>
                  : {comment.ownerReply}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={onSubmit} className="glass rounded-[var(--radius-card)] p-5">
        <p className="mb-4 text-sm text-[var(--text-muted)]">{labels.hint}</p>
        <label className="mb-3 block text-sm">
          {labels.name}
          <input
            className="mt-1 w-full rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-white"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
          />
        </label>
        <label className="mb-3 block text-sm">
          {labels.email}
          <input
            type="email"
            className="mt-1 w-full rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-white"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label className="mb-4 block text-sm">
          {labels.body}
          <textarea
            className="mt-1 w-full rounded-[var(--radius-card)] border border-white/15 bg-white/5 px-3 py-2 text-white"
            rows={4}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            required
          />
        </label>
        {message ? (
          <p className="mb-3 text-sm text-[var(--accent-link)]">{message}</p>
        ) : null}
        {error ? (
          <p className="mb-3 text-sm text-[var(--accent-cta)]">{error}</p>
        ) : null}
        <button type="submit" className="btn-cta" disabled={sending}>
          {sending ? labels.sending : labels.submit}
        </button>
      </form>
    </section>
  );
}
