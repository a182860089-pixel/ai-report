"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { T } from "@/components/Text";
import { AdminAuthProvider, useAdminAuth } from "@/lib/admin-auth";
import { useLocale } from "@/lib/locale";
import "./admin.css";

const NAV = [
  { href: "/admin", zh: "案头", en: "Desk", exact: true },
  { href: "/admin/briefings", zh: "早报", en: "Briefings", exact: false },
  { href: "/admin/topics", zh: "专题", en: "Topics", exact: false },
  { href: "/admin/sources", zh: "信源", en: "Sources", exact: false },
  { href: "/admin/pipeline", zh: "采集", en: "Pipeline", exact: false },
  { href: "/admin/audit", zh: "审计", en: "Audit", exact: false }
];

function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { ready, email, logout } = useAdminAuth();
  const { locale, setLocale } = useLocale();

  useEffect(() => {
    if (!ready) return;
    if (pathname === "/admin/login") return;
    if (!email) {
      const next = pathname && pathname !== "/admin" ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/admin/login${next}`);
    }
  }, [ready, email, pathname, router]);

  if (!ready) {
    return (
      <div className="desk-boot">
        <T zh="开台…" en="Opening desk…" />
      </div>
    );
  }

  if (pathname === "/admin/login") return <>{children}</>;
  if (!email) return <div className="desk-boot" />;

  return (
    <div className="desk">
      <aside className="desk-rail">
        <div className="desk-brand">
          AI 日报
          <small>Copy desk</small>
        </div>
        <nav className="desk-nav" aria-label="Desk">
          {NAV.map((item) => {
            const current = item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link key={item.href} href={item.href} aria-current={current ? "page" : undefined}>
                <T zh={item.zh} en={item.en} />
              </Link>
            );
          })}
        </nav>
        <div className="desk-rail-foot">
          <span>
            <T zh="在岗" en="Signed in" />
            <br />
            <b>{email}</b>
          </span>
          <div className="lang" role="group" aria-label={locale === "zh" ? "语言" : "Language"}>
            <button type="button" className="press" aria-pressed={locale === "zh"} onClick={() => setLocale("zh")}>
              中
            </button>
            <button type="button" className="press" aria-pressed={locale === "en"} onClick={() => setLocale("en")}>
              EN
            </button>
          </div>
          <Link href="/"> 
            <T zh="看报纸" en="Open gazette" />
          </Link>
          <button
            type="button"
            className="desk-btn ghost"
            onClick={async () => {
              await logout();
              router.replace("/admin/login");
            }}
          >
            <T zh="下班" en="Sign out" />
          </button>
        </div>
      </aside>
      <div className="desk-main">{children}</div>
    </div>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminShell>{children}</AdminShell>
    </AdminAuthProvider>
  );
}