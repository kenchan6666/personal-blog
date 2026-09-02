"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import type { Dictionary } from "@/i18n/dictionaries";
import type { Locale } from "@/i18n/config";
import { requestOtp, setSessionToken, verifyOtp } from "@/lib/api";

type Props = {
  locale: Locale;
  dict: Dictionary;
};

function mapError(message: string, dict: Dictionary): string {
  switch (message) {
    case "email_not_allowed":
      return dict.admin.errorNotAllowed;
    case "invalid_otp":
      return dict.admin.errorInvalid;
    case "rate_limited":
      return dict.admin.errorRate;
    case "smtp_failed":
      return dict.admin.errorSmtp;
    case "Failed to fetch":
    case "NetworkError when attempting to fetch resource.":
      return dict.admin.errorNetwork;
    default:
      if (message.startsWith("http_") || message.includes("Timeout")) {
        return dict.admin.errorNetwork;
      }
      return `${dict.admin.errorGeneric} (${message || "unknown"})`;
  }
}

export function AdminLoginForm({ locale, dict }: Props) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState<"idle" | "send" | "verify">("idle");
  const [error, setError] = useState<string | null>(null);

  async function onSend(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy("send");
    try {
      await requestOtp(email.trim());
      setSent(true);
    } catch (err) {
      setError(mapError(err instanceof Error ? err.message : "", dict));
    } finally {
      setBusy("idle");
    }
  }

  async function onVerify(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy("verify");
    try {
      const { session_token } = await verifyOtp(email.trim(), code.trim());
      setSessionToken(session_token);
      router.replace(`/${locale}/admin`);
    } catch (err) {
      setError(mapError(err instanceof Error ? err.message : "", dict));
    } finally {
      setBusy("idle");
    }
  }

  return (
    <div className="glass mx-auto w-full max-w-md rounded-[var(--radius-panel)] p-8">
      <h1 className="display-font mb-6 text-2xl font-bold">{dict.admin.title}</h1>

      <form className="space-y-4" onSubmit={sent ? onVerify : onSend}>
        <label className="block space-y-2 text-sm">
          <span className="text-[var(--text-muted)]">{dict.admin.email}</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="field field-tight py-2.5"
          />
        </label>

        {sent && (
          <label className="block space-y-2 text-sm">
            <span className="text-[var(--text-muted)]">{dict.admin.code}</span>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="field field-tight py-2.5 tracking-[0.3em]"
            />
          </label>
        )}

        {sent && (
          <p className="text-sm text-[var(--text-muted)]">{dict.admin.sentHint}</p>
        )}

        {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

        <button type="submit" className="btn-cta w-full" disabled={busy !== "idle"}>
          {busy === "send"
            ? dict.admin.sending
            : busy === "verify"
              ? dict.admin.verifying
              : sent
                ? dict.admin.verify
                : dict.admin.sendCode}
        </button>
      </form>
    </div>
  );
}
