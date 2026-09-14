"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { SearchIcon, SunIcon } from "./Icons";
import { T } from "./Text";
import { useLocale } from "@/lib/locale";

const NAV = [
  { href: "/", zh: "今日", en: "Today", match: (path: string) => path === "/" || path.startsWith("/d/") },
  { href: "/archive", zh: "归档", en: "Archive", match: (path: string) => path.startsWith("/archive") },
  { href: "/topics", zh: "专题", en: "Topics", match: (path: string) => path.startsWith("/topics") },
  { href: "/sources", zh: "信源", en: "Sources", match: (path: string) => path.startsWith("/sources") },
  { href: "/search", zh: "搜索", en: "Search", match: (path: string) => path.startsWith("/search") }
];

function isTypingTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { locale, setLocale } = useLocale();

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (isTypingTarget(event.target)) {
        if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
          event.preventDefault();
          document.querySelector<HTMLInputElement>("input[type=search]")?.focus();
        }
        return;
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (pathname === "/search") {
          document.querySelector<HTMLInputElement>("input[type=search]")?.focus();
        } else {
          router.push("/search");
        }
        return;
      }
      if (event.key === "/") {
        event.preventDefault();
        if (pathname === "/search") {
          document.querySelector<HTMLInputElement>("input[type=search]")?.focus();
        } else {
          router.push("/search");
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pathname, router]);

  return (
    <header className="masthead">
      <div className="masthead-row">
        <Link className="brand press" href="/">
          <SunIcon />
          <span>AI 日报</span>
        </Link>
        <div className="masthead-actions">
          <div className="lang" role="group" aria-label={locale === "zh" ? "语言" : "Language"}>
            <button
              type="button"
              className="press"
              aria-pressed={locale === "zh"}
              onClick={() => setLocale("zh")}
            >
              中
            </button>
            <button
              type="button"
              className="press"
              aria-pressed={locale === "en"}
              onClick={() => setLocale("en")}
            >
              EN
            </button>
          </div>
          <Link className="icon-btn press" href="/search" aria-label={locale === "zh" ? "搜索" : "Search"}>
            <SearchIcon />
          </Link>
        </div>
      </div>
      <nav className="nav" aria-label={locale === "zh" ? "栏目" : "Site"}>
        {NAV.map((item) => {
          const current = item.match(pathname);
          return (
            <Link
              key={item.href}
              className="press"
              href={item.href}
              aria-current={current ? "page" : undefined}
            >
              <T zh={item.zh} en={item.en} />
            </Link>
          );
        })}
      </nav>
    </header>
  );
}