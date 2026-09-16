"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { T } from "@/components/Text";
import { Banner, Stamp, asErrorMessage } from "@/components/admin/ui";
import { adminApi, type AdminBriefingListItem, type AdminSource, type AuditItem } from "@/lib/admin-api";
import { isoDate } from "@/lib/dates";

function windowRange() {
  const to = new Date();
  to.setDate(to.getDate() + 7);
  const from = new Date(to);
  from.setDate(from.getDate() - 60);
  return {
    from: isoDate(from.getFullYear(), from.getMonth() + 1, from.getDate()),
    to: isoDate(to.getFullYear(), to.getMonth() + 1, to.getDate())
  };
}

export default function AdminDeskPage() {
  const [error, setError] = useState<string | null>(null);
  const [briefings, setBriefings] = useState<AdminBriefingListItem[]>([]);
  const [sources, setSources] = useState<AdminSource[]>([]);
  const [audits, setAudits] = useState<AuditItem[]>([]);

  useEffect(() => {
    const { from, to } = windowRange();
    Promise.all([adminApi.briefings(from, to), adminApi.sources(), adminApi.audit(8)])
      .then(([items, src, logs]) => {
        setBriefings(items.slice().sort((a, b) => b.date.localeCompare(a.date)));
        setSources(src);
        setAudits(logs);
      })
      .catch((err) => setError(asErrorMessage(err)));
  }, []);

  const published = briefings.filter((item) => item.status === "published");
  const drafts = briefings.filter((item) => item.status === "draft");
  const sick = sources.filter((item) => item.status === "bad" || item.isQuarantined);
  const latest = published[0];

  return (
    <section>
      <div className="desk-kicker">DESK</div>
      <h1 className="desk-title">
        <T zh="今日划版" en="Today’s slate" />
      </h1>
      <p className="desk-lead">
        <T zh="公开页只读 published。草稿待在案头，脉搏数字不会被簇数偷偷改掉。" en="The gazette only shows published copy. Drafts stay here. Pulse numbers are snapshots." />
      </p>
      {error ? <Banner kind="error">{error}</Banner> : null}
      <div className="desk-toolbar">
        <Link className="desk-btn primary" href="/admin/briefings">
          <T zh="新早报" en="New briefing" />
        </Link>
        {latest ? (
          <Link className="desk-btn" href={`/d/${latest.date}`}>
            <T zh="看付印页" en="Open live page" />
          </Link>
        ) : null}
      </div>
      <div className="desk-panels">
        <div className="desk-panel">
          <h2>
            <T zh="付印" en="Live" /> · {published.length}
          </h2>
          {published.map((item) => (
            <p key={item.date}>
              <Stamp status="published" />{" "}
              <Link href={`/admin/briefings/${item.date}`}>
                <span className="desk-mono">{item.date}</span> {item.title.zh}
              </Link>
            </p>
          ))}
        </div>
        <div className="desk-panel">
          <h2>
            <T zh="校样" en="Drafts" /> · {drafts.length}
          </h2>
          {drafts.length === 0 ? (
            <p className="desk-hint">
              <T zh="没有草稿。" en="No drafts." />
            </p>
          ) : (
            drafts.map((item) => (
              <p key={item.date}>
                <Stamp status="draft" />{" "}
                <Link href={`/admin/briefings/${item.date}`}>
                  <span className="desk-mono">{item.date}</span> {item.title.zh}
                </Link>
              </p>
            ))
          )}
        </div>
        <div className="desk-panel">
          <h2>
            <T zh="信源告警" en="Source alerts" />
          </h2>
          {sick.length === 0 ? (
            <p className="desk-hint">
              <T zh="目录里没有隔离或 bad 源。" en="No quarantined or bad sources." />
            </p>
          ) : (
            sick.map((item) => (
              <p key={item.id}>
                <span className="desk-mono">{item.id}</span> {item.name} · {item.status}
              </p>
            ))
          )}
        </div>
        <div className="desk-panel">
          <h2>
            <T zh="最近动手" en="Recent actions" />
          </h2>
          {audits.map((item, index) => (
            <p key={`${item.createdAt}-${index}`}>
              <span className="desk-mono">{item.action}</span> {item.resource}
            </p>
          ))}
        </div>
      </div>
    </section>
  );
}