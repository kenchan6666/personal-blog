import type { ReactNode } from "react";
import {
  detectContactKind,
  isExternalContactHref,
  normalizeContactHref,
  type ContactKind,
} from "@/lib/contact-link";

type ProfileLink = {
  label: string;
  url: string;
  order: number;
};

type Contact = {
  href: string;
  label: string;
  kind: ContactKind;
  external: boolean;
};

const icons: Record<ContactKind, ReactNode> = {
  email: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <rect x="3.2" y="5.2" width="17.6" height="13.6" rx="2" />
      <path d="m4.2 7.1 7.8 6.2 7.8-6.2" />
    </svg>
  ),
  phone: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M7.4 3.8h3.1l1.2 3.1-1.7 1.1a12.2 12.2 0 0 0 5.1 5.1l1.1-1.7 3.1 1.2v3.1c0 .8-.6 1.5-1.4 1.6A15.4 15.4 0 0 1 3.8 6.2c.1-.8.8-1.4 1.6-1.4Z" />
    </svg>
  ),
  github: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path
        fill="currentColor"
        stroke="none"
        d="M12 2C6.48 2 2 6.58 2 12.26c0 4.52 2.87 8.36 6.84 9.72.5.1.68-.22.68-.49 0-.24-.01-.87-.01-1.71-2.78.62-3.37-1.37-3.37-1.37-.45-1.18-1.11-1.5-1.11-1.5-.91-.64.07-.63.07-.63 1 .07 1.53 1.06 1.53 1.06.89 1.57 2.34 1.12 2.91.85.09-.67.35-1.12.63-1.37-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.7 0 0 .84-.27 2.75 1.05A9.3 9.3 0 0 1 12 6.84c.85 0 1.71.12 2.51.35 1.9-1.32 2.74-1.05 2.74-1.05.55 1.4.2 2.44.1 2.7.64.72 1.03 1.63 1.03 2.75 0 3.94-2.34 4.8-4.58 5.06.36.32.68.94.68 1.9 0 1.37-.01 2.47-.01 2.8 0 .27.18.6.69.49A10.05 10.05 0 0 0 22 12.26C22 6.58 17.52 2 12 2Z"
      />
    </svg>
  ),
  x: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path
        fill="currentColor"
        stroke="none"
        d="M16.6 3.2h3.1l-6.8 7.77 8 10.83h-6.26l-4.9-6.4-5.6 6.4H1.04l7.27-8.31L.64 3.2h6.42l4.42 5.85 5.12-5.85Zm-1.1 16.7h1.72L6.58 4.94H4.74l10.76 14.96Z"
      />
    </svg>
  ),
  telegram: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M21.2 4.6 3.7 11.3c-1.2.46-1.19 1.1-.22 1.39l4.5 1.4 1.74 5.34c.23.7.12.97.8.97.42 0 .6-.19.83-.42l2-1.94 4.16 3.07c.76.42 1.31.2 1.5-.71l2.72-12.82c.28-1.12-.43-1.63-1.53-1.28Z" />
      <path d="m10.1 14.05.4 4.18s.2.82.8 0l1.92-1.84" />
    </svg>
  ),
  whatsapp: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M12 3.4A8.6 8.6 0 0 0 4.7 16.7L3.4 20.6l4.05-1.27A8.6 8.6 0 1 0 12 3.4Z" />
      <path d="M9.2 8.85c.2-.45.4-.46.7-.46h.5c.18 0 .4 0 .58.45s.7 1.72.76 1.85c.06.12.1.28 0 .44-.1.16-.16.26-.32.41-.15.15-.32.34-.14.66.18.32.8 1.32 1.72 2.14 1.18 1.05 2.18 1.38 2.5 1.54.31.15.5.13.68-.08.18-.2.77-.9.98-1.2.2-.31.41-.25.7-.15.28.1 1.8.85 2.1 1 .31.16.52.23.6.36.07.13.07.75-.18 1.47-.25.72-1.46 1.38-2.04 1.47-.53.08-1.2.12-3.46-.72-2.73-1.02-4.5-3.7-4.64-3.87-.13-.18-1.1-1.46-1.1-2.79 0-1.32.7-1.97.94-2.24Z" />
    </svg>
  ),
  rss: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <circle cx="6.4" cy="17.6" r="1.7" fill="currentColor" stroke="none" />
      <path d="M4.6 10.2a9.2 9.2 0 0 1 9.2 9.2" />
      <path d="M4.6 5.4A14 14 0 0 1 18.6 19.4" />
    </svg>
  ),
  linkedin: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <rect x="3.4" y="3.4" width="17.2" height="17.2" rx="2.2" />
      <path d="M8.2 10.2v6.6M8.2 7.5v.2M11.6 16.8v-4.1c0-1.4.8-2.1 1.9-2.1s1.9.8 1.9 2.1v4.1" />
    </svg>
  ),
  instagram: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <rect x="3.6" y="3.6" width="16.8" height="16.8" rx="5" />
      <circle cx="12" cy="12" r="3.6" />
      <circle cx="17.1" cy="6.9" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  ),
  youtube: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <rect x="2.6" y="6.2" width="18.8" height="11.6" rx="3.2" />
      <path fill="currentColor" stroke="none" d="M10.4 9.6v4.8l4.4-2.4z" />
    </svg>
  ),
  discord: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M8.4 7.2c1.4-.6 2.7-.8 3.6-.85.9.05 2.2.25 3.6.85 1.7.7 2.8 1.85 3.3 3.15.7 1.85.9 3.65.95 5.15 0 .15-.05.3-.15.4-1.05.9-2.1 1.5-3.1 1.9-.2.08-.42 0-.52-.18l-.55-1.05c1.05-.35 1.9-.85 2.55-1.4.15-.12.16-.34.02-.48-.12-.12-.32-.14-.47-.05-1.55.95-3.25 1.5-5.08 1.5s-3.53-.55-5.08-1.5c-.15-.09-.35-.07-.47.05-.14.14-.13.36.02.48.65.55 1.5 1.05 2.55 1.4l-.55 1.05c-.1.18-.32.26-.52.18-1-.4-2.05-1-3.1-1.9-.1-.1-.15-.25-.15-.4.05-1.5.25-3.3.95-5.15.5-1.3 1.6-2.45 3.3-3.15Z" />
      <circle cx="9.4" cy="12.4" r="1.15" fill="currentColor" stroke="none" />
      <circle cx="14.6" cy="12.4" r="1.15" fill="currentColor" stroke="none" />
    </svg>
  ),
  resume: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M7.2 3.6h7.1L19 8.4v12c0 .9-.7 1.6-1.6 1.6H7.2c-.9 0-1.6-.7-1.6-1.6V5.2c0-.9.7-1.6 1.6-1.6Z" />
      <path d="M14.2 3.8V8h4.6M8.4 12.2h7.2M8.4 15.4h7.2M8.4 18.5h4.6" />
    </svg>
  ),
  link: (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M10.2 13.8a4.2 4.2 0 0 0 6 0l2.4-2.4a4.2 4.2 0 0 0-6-6l-1.4 1.4" />
      <path d="M13.8 10.2a4.2 4.2 0 0 0-6 0L5.4 12.6a4.2 4.2 0 1 0 6 6l1.4-1.4" />
    </svg>
  ),
};

function toContacts(email: string, links: ProfileLink[]): Contact[] {
  const items: Contact[] = [];
  const trimmed = email.trim();
  if (trimmed) {
    items.push({
      href: `mailto:${trimmed}`,
      label: trimmed,
      kind: "email",
      external: false,
    });
  }
  for (const link of [...links].sort((a, b) => a.order - b.order)) {
    const raw = link.url.trim();
    if (!raw) continue;
    const label = link.label.trim() || raw;
    const href = normalizeContactHref(raw, label);
    items.push({
      href,
      label,
      kind: detectContactKind(href, label),
      external: isExternalContactHref(href),
    });
  }
  return items;
}

export function ProfileContacts({
  email,
  links,
}: {
  email: string;
  links: ProfileLink[];
}) {
  const contacts = toContacts(email, links);
  if (contacts.length === 0) return null;

  return (
    <ul className="profile-contacts">
      {contacts.map((contact) => (
        <li key={`${contact.kind}-${contact.href}`}>
          <a
            href={contact.href}
            className="profile-contact"
            aria-label={contact.label}
            title={contact.label}
            {...(contact.external
              ? { target: "_blank", rel: "noreferrer" }
              : {})}
          >
            {icons[contact.kind]}
          </a>
        </li>
      ))}
    </ul>
  );
}
