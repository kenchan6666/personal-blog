import type { Locale } from "./config";

const zhHant = {
  brand: "陳逸楠",
  nav: {
    home: "首頁",
    projects: "項目",
    articles: "文章",
    journals: "日誌",
    admin: "後台",
  },
  hero: {
    headline: "用作品說話的工程師作品集",
    support: "先認識我是誰、做過什麼；再透過文章與日誌看見思考的深度。",
    ctaProjects: "查看項目",
    ctaArticles: "閱讀文章",
  },
  localeName: "繁中",
  openMenu: "打開選單",
  closeMenu: "關閉選單",
  admin: {
    title: "後台登入",
    email: "電子郵件",
    code: "驗證碼",
    sendCode: "發送驗證碼",
    verify: "登入",
    sending: "發送中…",
    verifying: "驗證中…",
    sentHint: "驗證碼已發送到你的信箱（若 SMTP 已設定）。",
    dashboard: "後台",
    signedInAs: "目前登入",
    logout: "登出",
    ready: "已登入。內容 CMS 將在後續工單接上。",
    errorGeneric: "出了點問題，請再試一次。",
    errorNotAllowed: "此信箱無權限。",
    errorInvalid: "驗證碼無效或已過期。",
    errorRate: "請求過於頻繁，請稍後再試。",
  },
};

const en = {
  brand: "YN Chan",
  nav: {
    home: "Home",
    projects: "Projects",
    articles: "Articles",
    journals: "Journals",
    admin: "Admin",
  },
  hero: {
    headline: "A portfolio that leads with craft",
    support:
      "Meet who I am and what I’ve shipped—then read the articles and journals behind the work.",
    ctaProjects: "View projects",
    ctaArticles: "Read articles",
  },
  localeName: "EN",
  openMenu: "Open menu",
  closeMenu: "Close menu",
  admin: {
    title: "Admin sign-in",
    email: "Email",
    code: "One-time code",
    sendCode: "Send code",
    verify: "Sign in",
    sending: "Sending…",
    verifying: "Verifying…",
    sentHint: "If SMTP is configured, a code was sent to your inbox.",
    dashboard: "Admin",
    signedInAs: "Signed in as",
    logout: "Sign out",
    ready: "You are signed in. Content CMS arrives in later tickets.",
    errorGeneric: "Something went wrong. Try again.",
    errorNotAllowed: "This email is not allowed.",
    errorInvalid: "Invalid or expired code.",
    errorRate: "Too many requests. Please wait.",
  },
};

export type Dictionary = typeof zhHant;

const dictionaries: Record<Locale, Dictionary> = {
  "zh-Hant": zhHant,
  en,
};

export function getDictionary(locale: Locale): Dictionary {
  return dictionaries[locale];
}
