"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { loadAdminSession, loginAdmin, logoutAdmin, saveAdminSession } from "@/lib/admin-api";

type AdminAuthValue = {
  ready: boolean;
  email: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AdminAuthContext = createContext<AdminAuthValue | null>(null);

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    setEmail(loadAdminSession()?.email ?? null);
    setReady(true);
  }, []);

  const login = useCallback(async (nextEmail: string, password: string) => {
    const session = await loginAdmin(nextEmail, password);
    setEmail(session.email);
  }, []);

  const logout = useCallback(async () => {
    await logoutAdmin();
    setEmail(null);
  }, []);

  const value = useMemo(() => ({ ready, email, login, logout }), [ready, email, login, logout]);
  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>;
}

export function useAdminAuth() {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) throw new Error("useAdminAuth must be used under AdminAuthProvider");
  return ctx;
}

export function dropLocalSession() {
  saveAdminSession(null);
}