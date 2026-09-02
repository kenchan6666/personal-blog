"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import {
  fetchOwnerComments,
  getSessionToken,
  moderateOwnerComment,
  replyOwnerComment,
  type OwnerComment,
} from "@/lib/api";
import { CmsCard } from "./cms-card";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

function commentHref(locale: Locale, comment: OwnerComment): string {
  if (comment.targetType === "journal") {
    return `/${locale}/journals/${comment.targetSlug}`;
  }
  return `/${locale}/articles/${comment.targetSlug}`;
}

export function CommentModerator({ locale, dict }: Props) {
  const a = dict.admin;
  const [comments, setComments] = useState<OwnerComment[]>([]);
  const [replies, setReplies] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function reload(token: string) {
    const list = await fetchOwnerComments(token);
    setComments(list);
  }

  useEffect(() => {
    const token = getSessionToken();
    if (!token) return;
    reload(token).catch(() => setError(a.errorGeneric));
  }, [a.errorGeneric]);

  async function onModerate(id: string, action: "approve" | "reject") {
    const token = getSessionToken();
    if (!token) return;
    try {
      await moderateOwnerComment(token, id, action);
      await reload(token);
    } catch {
      setError(a.errorGeneric);
    }
  }

  async function onReply(id: string) {
    const token = getSessionToken();
    const body = replies[id]?.trim();
    if (!token || !body) return;
    try {
      await replyOwnerComment(token, id, body);
      setReplies((prev) => ({ ...prev, [id]: "" }));
      await reload(token);
    } catch {
      setError(a.errorGeneric);
    }
  }

  const pending = comments.filter((item) => item.status === "pending").length;
  const sorted = [...comments].sort((left, right) => {
    if (left.status === right.status) return 0;
    return left.status === "pending" ? -1 : 1;
  });

  return (
    <CmsCard
      title={a.commentModerator}
      action={
        pending > 0 ? (
          <span className="status-pill">{pending} {a.pending}</span>
        ) : null
      }
    >
      {error ? (
        <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>
      ) : null}
      {comments.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">{a.noComments}</p>
      ) : (
        <ul className="space-y-4">
          {sorted.map((comment) => (
            <li
              key={comment.id}
              className="rounded-[var(--radius-card)] border border-[var(--hairline)] p-4"
            >
              <p className="text-sm text-[var(--text-muted)]">
                <a
                  href={commentHref(locale, comment)}
                  target="_blank"
                  rel="noreferrer"
                  className="underline-offset-2 hover:underline"
                >
                  {a.viewPublic}
                </a>
                {" · "}
                {comment.targetType}/{comment.targetSlug}
                {" · "}
                {comment.status}
              </p>
              <p className="mt-1 font-semibold">
                {comment.displayName}{" "}
                <span className="font-normal text-[var(--text-muted)]">
                  {comment.email}
                </span>
              </p>
              <p className="mt-2 whitespace-pre-wrap">{comment.body}</p>
              {comment.ownerReply ? (
                <p className="mt-2 text-sm text-[var(--text-muted)]">
                  {a.ownerReply}: {comment.ownerReply}
                </p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-ghost text-xs"
                  onClick={() => void onModerate(comment.id, "approve")}
                >
                  {a.approve}
                </button>
                <button
                  type="button"
                  className="btn-ghost text-xs"
                  onClick={() => void onModerate(comment.id, "reject")}
                >
                  {a.reject}
                </button>
              </div>
              <div className="mt-3 flex gap-2">
                <input
                  className="field field-tight flex-1"
                  value={replies[comment.id] ?? ""}
                  onChange={(e) =>
                    setReplies((prev) => ({
                      ...prev,
                      [comment.id]: e.target.value,
                    }))
                  }
                  placeholder={a.replyPlaceholder}
                />
                <button
                  type="button"
                  className="btn-ghost text-xs"
                  onClick={() => void onReply(comment.id)}
                >
                  {a.reply}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </CmsCard>
  );
}
