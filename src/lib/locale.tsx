"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";
import type { Locale } from "@/data/types";

const STORAGE_KEY = "ai-report-locale";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
};

const LocaleContext = createContext<LocaleContextValue>({
  locale: "zh",
  setLocale: () => undefined
});

function applyLocale(locale: Locale) {
  document.documentElement.dataset.locale = locale;
  document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
}

export const LOCALE_BOOT = `(function(){try{var l=localStorage.getItem("${STORAGE_KEY}");if(l==="en"||l==="zh"){document.documentElement.dataset.locale=l;document.documentElement.lang=l==="zh"?"zh-CN":"en";}}catch(e){}})();`;

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (typeof document === "undefined") return "zh";
    return document.documentElement.dataset.locale === "en" ? "en" : "zh";
  });

  useEffect(() => {
    const current = document.documentElement.dataset.locale;
    if (current === "en" || current === "zh") {
      setLocaleState(current);
    }
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    applyLocale(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore quota / private mode */
    }
  }, []);

  const value = useMemo(() => ({ locale, setLocale }), [locale, setLocale]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  return useContext(LocaleContext);
}