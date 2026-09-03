const CJK = /[\u4e00-\u9fff]/;

export function nextTypedText(shown: string, target: string): string {
  if (!target) return "";
  const prefix = target.startsWith(shown) ? shown : "";
  if (prefix.length >= target.length) return target;
  const ch = target[prefix.length] ?? "";
  const step = CJK.test(ch) ? 1 : 2;
  return target.slice(0, prefix.length + step);
}

export function typewriterDelayMs(shown: string, target: string): number {
  const ch = target[shown.length] ?? "";
  return CJK.test(ch) ? 26 : 14;
}
