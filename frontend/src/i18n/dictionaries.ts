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
};

export type Dictionary = typeof zhHant;

const dictionaries: Record<Locale, Dictionary> = {
  "zh-Hant": zhHant,
  en,
};

export function getDictionary(locale: Locale): Dictionary {
  return dictionaries[locale];
}
