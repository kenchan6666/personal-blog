import Link from "next/link";

type Action = { href: string; label: string };

type Props = {
  title: string;
  body: string;
  actions?: Action[];
  compact?: boolean;
};

/** Calm, designed empty state: a soft glyph, one line of intent, and a way on. */
export function EmptyState({ title, body, actions = [], compact = false }: Props) {
  return (
    <div className={`card empty-state${compact ? " is-compact" : ""}`}>
      <span className="empty-state-glyph" aria-hidden>
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
          <path
            d="M7 3.75h7.5L19 8.25V19a1.25 1.25 0 0 1-1.25 1.25H7A1.25 1.25 0 0 1 5.75 19V5A1.25 1.25 0 0 1 7 3.75Z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path
            d="M14.25 3.75V8.5h4.75M9 12.5h6M9 15.75h4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <p className="empty-state-title">{title}</p>
      <p className="empty-state-body">{body}</p>
      {actions.length > 0 ? (
        <p className="empty-state-actions">
          {actions.map((action) => (
            <Link key={action.href} href={action.href} className="empty-state-link">
              {action.label} <span aria-hidden>→</span>
            </Link>
          ))}
        </p>
      ) : null}
    </div>
  );
}
