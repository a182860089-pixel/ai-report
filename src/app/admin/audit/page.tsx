"use client";

import { useEffect, useState } from "react";
import { T } from "@/components/Text";
import { Banner, asErrorMessage } from "@/components/admin/ui";
import { adminApi, type AuditItem } from "@/lib/admin-api";

export default function AdminAuditPage() {
  const [items, setItems] = useState<AuditItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminApi.audit(100).then(setItems).catch((err) => setError(asErrorMessage(err)));
  }, []);

  return (
    <section>
      <div className="desk-kicker">AUDIT</div>
      <h1 className="desk-title">
        <T zh="动手记录" en="Action log" />
      </h1>
      <p className="desk-lead">
        <T zh="只读。没有 token，没有内部 id。" en="Read-only. No tokens, no internal ids." />
      </p>
      {error ? <Banner kind="error">{error}</Banner> : null}
      <table className="desk-table">
        <thead>
          <tr>
            <th>time</th>
            <th>action</th>
            <th>resource</th>
            <th>actor</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={`${item.createdAt}-${index}`}>
              <td className="desk-mono">{item.createdAt.replace("T", " ").replace("Z", "")}</td>
              <td className="desk-mono">{item.action}</td>
              <td>{item.resource}</td>
              <td>{item.actorEmail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}