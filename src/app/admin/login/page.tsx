"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { T } from "@/components/Text";
import { Banner, asErrorMessage } from "@/components/admin/ui";
import { useAdminAuth } from "@/lib/admin-auth";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { ready, email, login } = useAdminAuth();
  const [account, setAccount] = useState("admin@example.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const next = params.get("next") || "/admin";

  useEffect(() => {
    if (ready && email) router.replace(next.startsWith("/admin") ? next : "/admin");
  }, [ready, email, next, router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(account.trim(), password);
      router.replace(next.startsWith("/admin") ? next : "/admin");
    } catch (err) {
      setError(asErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="desk-login">
      <form className="desk-login-card desk-form" onSubmit={onSubmit}>
        <div className="desk-kicker">COPY DESK</div>
        <h1>
          <T zh="编辑部开门" en="Open the desk" />
        </h1>
        {error ? <Banner kind="error">{error}</Banner> : null}
        <label className="desk-field">
          <span className="desk-label">Email</span>
          <input type="email" autoComplete="username" value={account} onChange={(e) => setAccount(e.currentTarget.value)} required />
        </label>
        <label className="desk-field">
          <span className="desk-label">
            <T zh="密码" en="Password" />
          </span>
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.currentTarget.value)} required />
        </label>
        <button className="desk-btn primary" type="submit" disabled={busy}>
          {busy ? <T zh="在验…" en="Checking…" /> : <T zh="登录" en="Sign in" />}
        </button>
      </form>
    </div>
  );
}

export default function AdminLoginPage() {
  return (
    <Suspense fallback={<div className="desk-boot">…</div>}>
      <LoginForm />
    </Suspense>
  );
}