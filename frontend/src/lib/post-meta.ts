import type { Locale } from "@/i18n/config";

const ZH_MONTHS = [
  "一月",
  "二月",
  "三月",
  "四月",
  "五月",
  "六月",
  "七月",
  "八月",
  "九月",
  "十月",
  "十一月",
  "十二月",
];

const EN_MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export function parsePostDate(iso: string): Date {
  return new Date(iso);
}

export function monthLabel(iso: string, locale: Locale): string {
  const month = parsePostDate(iso).getMonth();
  return locale === "zh-Hant" ? ZH_MONTHS[month] : EN_MONTHS[month];
}

export function formatPostDate(iso: string, locale: Locale): string {
  const date = parsePostDate(iso);
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  if (locale === "zh-Hant") {
    return `${year} 年 ${month} 月 ${day} 日`;
  }
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatCompactDate(iso: string): string {
  const date = parsePostDate(iso);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${month}-${day}`;
}

export function formatCount(template: string, n: number): string {
  return template.replace("{n}", String(n));
}
