import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import {
  Geist_Mono,
  Noto_Sans_SC,
  Noto_Sans_TC,
  Space_Grotesk,
} from "next/font/google";
import { SiteShell } from "@/components/site-shell";
import { ThemeScript } from "@/components/theme-script";
import { defaultLocale, isLocale } from "@/i18n/config";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const notoSansTC = Noto_Sans_TC({
  variable: "--font-noto-sans-tc",
  weight: ["400", "700"],
  display: "swap",
  preload: false,
});

const notoSansSC = Noto_Sans_SC({
  variable: "--font-noto-sans-sc",
  weight: ["400", "700"],
  display: "swap",
  preload: false,
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ken",
  description: "Job-seeking personal portfolio — projects, articles, journals.",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/mascot.png", type: "image/png", sizes: "512x512" },
    ],
    apple: { url: "/mascot-apple.png", sizes: "180x180" },
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const raw = (await headers()).get("x-locale") ?? defaultLocale;
  const locale = isLocale(raw) ? raw : defaultLocale;
  return (
    <html
      lang={locale}
      suppressHydrationWarning
      className={`${spaceGrotesk.variable} ${notoSansTC.variable} ${notoSansSC.variable} ${geistMono.variable} locale-${locale} h-full antialiased`}
    >
      <body className="min-h-full">
        <ThemeScript />
        <div className="ambient" aria-hidden>
          <span className="ambient-orb ambient-orb-a" />
          <span className="ambient-orb ambient-orb-b" />
          <span className="ambient-orb ambient-orb-c" />
        </div>
        <SiteShell>{children}</SiteShell>
      </body>
    </html>
  );
}
