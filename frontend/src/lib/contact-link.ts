export type ContactKind =
  | "email"
  | "phone"
  | "github"
  | "x"
  | "telegram"
  | "whatsapp"
  | "rss"
  | "linkedin"
  | "instagram"
  | "youtube"
  | "discord"
  | "resume"
  | "link";

export type ContactPreset = {
  id: ContactKind;
  labelZh: string;
  labelHans: string;
  labelEn: string;
  placeholder: string;
};

export const CONTACT_PRESETS: ContactPreset[] = [
  { id: "github", labelZh: "GitHub", labelHans: "GitHub", labelEn: "GitHub", placeholder: "https://github.com/you" },
  { id: "phone", labelZh: "電話", labelHans: "电话", labelEn: "Phone", placeholder: "+852 1234 5678" },
  { id: "whatsapp", labelZh: "WhatsApp", labelHans: "WhatsApp", labelEn: "WhatsApp", placeholder: "+852 1234 5678" },
  { id: "x", labelZh: "推特", labelHans: "推特", labelEn: "Twitter", placeholder: "https://x.com/you" },
  { id: "telegram", labelZh: "Telegram", labelHans: "Telegram", labelEn: "Telegram", placeholder: "@username" },
  { id: "linkedin", labelZh: "LinkedIn", labelHans: "LinkedIn", labelEn: "LinkedIn", placeholder: "https://linkedin.com/in/you" },
];

function hostOf(url: string): string {
  try {
    const href = /^(https?:|mailto:|tel:)/i.test(url) ? url : `https://${url}`;
    return new URL(href).hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}

function looksLikePhone(value: string): boolean {
  const trimmed = value.trim();
  if (/^tel:/i.test(trimmed)) return true;
  const digits = trimmed.replace(/\D/g, "");
  return digits.length >= 8 && /^[+]?[\d\s()\-.]{8,20}$/.test(trimmed);
}

export function detectContactKind(url: string, label: string): ContactKind {
  const href = url.trim();
  const host = hostOf(href);
  const text = `${href} ${label}`.toLowerCase();
  if (href.startsWith("mailto:") || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(href)) {
    return "email";
  }
  if (host === "github.com" || host.endsWith(".github.com") || /\bgithub\b/.test(text)) {
    return "github";
  }
  if (
    host === "x.com" ||
    host.endsWith(".x.com") ||
    host === "twitter.com" ||
    host.endsWith(".twitter.com") ||
    text.includes("twitter") ||
    text.includes("推特")
  ) {
    return "x";
  }
  if (host === "t.me" || host.includes("telegram") || text.includes("telegram")) {
    return "telegram";
  }
  if (host === "wa.me" || host.includes("whatsapp") || text.includes("whatsapp")) {
    return "whatsapp";
  }
  if (href.toLowerCase().includes("/feed") || /\.(rss|atom)(\?|$)/i.test(href) || text.includes("rss")) {
    return "rss";
  }
  if (host.includes("linkedin") || text.includes("linkedin")) return "linkedin";
  if (host.includes("instagram") || text.includes("instagram")) return "instagram";
  if (host.includes("youtube") || host === "youtu.be" || text.includes("youtube")) {
    return "youtube";
  }
  if (host.includes("discord") || text.includes("discord")) return "discord";
  if (/\.pdf(\?|$)/i.test(href) || /resume|curriculum|\bcv\b|簡歷|履歷|简历/.test(text)) {
    return "resume";
  }
  if (
    href.startsWith("tel:") ||
    looksLikePhone(href) ||
    /電話|电话|\bphone\b|\btel\b/.test(text)
  ) {
    return "phone";
  }
  return "link";
}

export function normalizeContactHref(url: string, label: string): string {
  const raw = url.trim();
  if (!raw) return "";
  const kind = detectContactKind(raw, label);

  if (/^(https?:|mailto:|tel:)/i.test(raw)) return raw;
  if (kind === "email" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(raw)) {
    return `mailto:${raw}`;
  }
  if (kind === "phone" || looksLikePhone(raw)) {
    return `tel:${raw.replace(/[^\d+]/g, "")}`;
  }
  if (kind === "whatsapp") {
    const digits = raw.replace(/\D/g, "");
    if (digits) return `https://wa.me/${digits}`;
  }
  if (kind === "x") {
    const handle = raw.replace(/^@/, "");
    if (handle && !handle.includes("/")) return `https://x.com/${handle}`;
  }
  if (kind === "github") {
    const handle = raw.replace(/^@/, "");
    if (handle && !handle.includes("/")) return `https://github.com/${handle}`;
  }
  if (kind === "telegram") {
    const handle = raw.replace(/^@/, "");
    if (handle && !handle.includes("/")) return `https://t.me/${handle}`;
  }
  if (kind === "linkedin" && !raw.includes(".")) {
    return `https://www.linkedin.com/in/${raw.replace(/^@/, "")}`;
  }
  return /^https?:/i.test(raw) ? raw : `https://${raw}`;
}

export function isExternalContactHref(href: string): boolean {
  return /^(https?:)/i.test(href);
}
