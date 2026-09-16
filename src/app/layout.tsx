import type { Metadata, Viewport } from "next";
import { LocaleProvider, LOCALE_BOOT } from "@/lib/locale";
import "./globals.css";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: {
    default: "AI 日报",
    template: "%s · AI 日报"
  },
  description: "每日 AI 事件簇早报。按事件读，不按网站刷。"
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#1c1c1e" }
  ]
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" data-locale="zh" suppressHydrationWarning>
      <body>
        <script dangerouslySetInnerHTML={{ __html: LOCALE_BOOT }} />
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}