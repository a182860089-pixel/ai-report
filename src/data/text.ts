import type { Text } from "./types";

export const tx = (zh: string, en: string): Text => ({ zh, en });

export function src(
  name: string,
  lang: "zh" | "en",
  kindZh: string,
  kindEn: string,
  time: string
) {
  return { name, lang, kind: tx(kindZh, kindEn), time };
}