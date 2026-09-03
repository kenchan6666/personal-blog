import type { AboutKind, Localized } from "@/lib/api";
import { emptyLocalized } from "@/lib/api";

export const ABOUT_KIND_TITLES: Record<AboutKind, Localized> = {
  summary: {
    "zh-Hant": "自我描述",
    "zh-Hans": "自我描述",
    en: "About me",
  },
  education: {
    "zh-Hant": "學歷",
    "zh-Hans": "学历",
    en: "Education",
  },
  experience: {
    "zh-Hant": "經歷",
    "zh-Hans": "经历",
    en: "Experience",
  },
  achievement: {
    "zh-Hant": "成績與獎項",
    "zh-Hans": "成绩与奖项",
    en: "Achievements",
  },
  custom: {
    "zh-Hant": "",
    "zh-Hans": "",
    en: "",
  },
};

export const ABOUT_KIND_BODIES: Record<AboutKind, Localized> = {
  summary: {
    "zh-Hant":
      "我是 **名字**，一句定位（例如：寫程式、打太鼓的人）。\n\n再寫兩三段自我描述：從哪裡來、現在在做什麼、為什麼寫這個站。可插入一張生活或作品照。",
    "zh-Hans":
      "我是 **名字**，一句定位（例如：写程序、打太鼓的人）。\n\n再写两三段自我描述：从哪里来、现在在做什么、为什么写这个站。可插入一张生活或作品照。",
    en: "I am **Name**, a one-line positioning sentence.\n\nThen two or three short paragraphs: where you come from, what you do now, and why this site exists. A photo is welcome.",
  },
  education: {
    "zh-Hant":
      "- **香港大學** · 計算機科學學士 · 2020–2024\n- **某某中學** · 2014–2020",
    "zh-Hans":
      "- **香港大学** · 计算机科学学士 · 2020–2024\n- **某某中学** · 2014–2020",
    en: "- **The University of Hong Kong** · BEng Computer Science · 2020–2024\n- **High school** · 2014–2020",
  },
  experience: {
    "zh-Hant":
      "### 職稱 · 機構名稱\n\n2023.09 – 2025.09\n\n一兩段說明職責、成果，或一段你真正在意的經歷。\n\n### 另一段經歷\n\n2022 – 2023\n\n補充說明。",
    "zh-Hans":
      "### 职称 · 机构名称\n\n2023.09 – 2025.09\n\n一两段说明职责、成果，或一段你真正在意的经历。\n\n### 另一段经历\n\n2022 – 2023\n\n补充说明。",
    en: "### Title · Organization\n\n2023.09 – 2025.09\n\nA short account of the work, outcomes, or the part that still matters.\n\n### Another role\n\n2022 – 2023\n\nNotes.",
  },
  achievement: {
    "zh-Hant":
      "- **獎項或成績名稱** · 2024 · 一句說明\n- **證書 / 比賽 / 公開成果** · 2023",
    "zh-Hans":
      "- **奖项或成绩名称** · 2024 · 一句说明\n- **证书 / 比赛 / 公开成果** · 2023",
    en: "- **Award or result** · 2024 · one-line note\n- **Certificate / contest / public work** · 2023",
  },
  custom: {
    "zh-Hant":
      "### 小節標題\n\n像個人誌那樣寫：興趣、寫作習慣、使用的工具，或任何你想公開的段落。",
    "zh-Hans":
      "### 小节标题\n\n像个人志那样写：兴趣、写作习惯、使用的工具，或任何你想公开的段落。",
    en: "### Subsection\n\nWrite it like a personal note: interests, how you write, tools you use, or anything else you want public.",
  },
};

export const ABOUT_KIND_ORDER: AboutKind[] = [
  "summary",
  "education",
  "experience",
  "achievement",
  "custom",
];

export const ABOUT_KIND_SLUG: Record<AboutKind, string> = {
  summary: "summary",
  education: "education",
  experience: "experience",
  achievement: "achievement",
  custom: "note",
};

const ABOUT_KIND_BASE_ORDER: Record<AboutKind, number> = {
  summary: 0,
  education: 10,
  experience: 20,
  achievement: 30,
  custom: 40,
};

export function localizedIsEmpty(value: Localized | undefined): boolean {
  if (!value) return true;
  return !value["zh-Hant"]?.trim() && !value["zh-Hans"]?.trim() && !value.en?.trim();
}

export function localizedEqual(
  left: Localized | undefined,
  right: Localized | undefined,
): boolean {
  const a = filledOrEmpty(left);
  const b = filledOrEmpty(right);
  return a["zh-Hant"] === b["zh-Hant"] && a["zh-Hans"] === b["zh-Hans"] && a.en === b.en;
}

export function slugForAboutKind(kind: AboutKind, taken: Iterable<string>): string {
  const base = ABOUT_KIND_SLUG[kind];
  const used = new Set(taken);
  if (!used.has(base)) return base;
  let n = 2;
  while (used.has(`${base}-${n}`)) n += 1;
  return `${base}-${n}`;
}

export function nextAboutOrder(
  kind: AboutKind,
  modules: { kind: AboutKind; order: number }[],
): number {
  const same = modules.filter((item) => item.kind === kind);
  if (same.length === 0) return ABOUT_KIND_BASE_ORDER[kind];
  return Math.max(...same.map((item) => item.order)) + 1;
}

export function draftAboutModule(
  kind: AboutKind,
  existing: { slug: string; kind: AboutKind; order: number }[],
): {
  slug: string;
  kind: AboutKind;
  title: Localized;
  body: Localized;
  status: "draft" | "published";
  order: number;
} {
  return {
    slug: slugForAboutKind(
      kind,
      existing.map((item) => item.slug),
    ),
    kind,
    title: ABOUT_KIND_TITLES[kind],
    body: ABOUT_KIND_BODIES[kind],
    status: "draft",
    order: nextAboutOrder(kind, existing),
  };
}

export function applyAboutKindChange(
  current: {
    id?: string;
    slug: string;
    kind: AboutKind;
    title: Localized;
    body: Localized;
  },
  nextKind: AboutKind,
  takenSlugs: Iterable<string>,
): {
  slug: string;
  kind: AboutKind;
  title: Localized;
  body: Localized;
} {
  if (current.id) {
    return {
      slug: current.slug,
      kind: nextKind,
      title: current.title,
      body: current.body,
    };
  }
  const prev = current.kind;
  const titleDefault =
    localizedIsEmpty(current.title) ||
    localizedEqual(current.title, ABOUT_KIND_TITLES[prev]);
  const bodyDefault =
    localizedIsEmpty(current.body) ||
    localizedEqual(current.body, ABOUT_KIND_BODIES[prev]);
  const slugDefault =
    !current.slug.trim() ||
    current.slug === ABOUT_KIND_SLUG[prev] ||
    current.slug.startsWith(`${ABOUT_KIND_SLUG[prev]}-`);
  return {
    kind: nextKind,
    title: titleDefault ? ABOUT_KIND_TITLES[nextKind] : current.title,
    body: bodyDefault ? ABOUT_KIND_BODIES[nextKind] : current.body,
    slug: slugDefault ? slugForAboutKind(nextKind, takenSlugs) : current.slug,
  };
}

export function filledOrEmpty(value: Localized | undefined): Localized {
  return value ?? emptyLocalized();
}

export function appendMarkdownToAll(value: Localized, snippet: string): Localized {
  const next = filledOrEmpty(value);
  return {
    "zh-Hant": `${next["zh-Hant"]}${snippet}`,
    "zh-Hans": `${next["zh-Hans"]}${snippet}`,
    en: `${next.en}${snippet}`,
  };
}
