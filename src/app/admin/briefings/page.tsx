"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { T } from "@/components/Text";
import { Banner, Field, Stamp, TextPair, asErrorMessage } from "@/components/admin/ui";
import { adminApi, type AdminBriefingListItem } from "@/lib/admin-api";
import { isoDate } from "@/lib/dates";

function windowRange() {
  const to = new Date();
  to.setDate(to.getDate() + 14);
  const from = new Date(to);
  from.setDate(from.getDate() - 48);
  return {
    from: isoDate(from.getFullYear(), from.getMonth() + 1, from.getDate()),
    to: isoDate(to.getFullYear(), to.getMonth() + 1, to.getDate())
  };
}

const emptyPulse = {
  clusters: 0,
  articles: 0,
  zhEn: "0 : 0",
  healthy: 0,
  totalSources: 26,
  topics: [] as { name: { zh: string; en: string }; count: number }[]
};

export default function AdminBriefingsPage() {
  const [items, setItems] = useState<AdminBriefingListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [title, setTitle] = useState({ zh: "", en: "" });
  const [moreHeading, setMoreHeading] = useState({ zh: "更多", en: "More" });
  const [lede, setLede] = useState({ zh: "", en: "" });
  const [updatedAt, setUpdatedAt] = useState("07:00");

  async function reload() {
    const { from, to } = windowRange();
    setItems(await adminApi.briefings(from, to));
  }

  useEffect(() => {
    reload().catch((err) => setError(asErrorMessage(err)));
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setOk(null);
    try {
      await adminApi.createBriefing({
        date,
        title,
        moreHeading,
        lede: lede.zh.trim() && lede.en.trim() ? [lede] : [],
        updatedAt,
        pulse: emptyPulse
      });
      setOk("Draft created.");
      await reload();
    } catch (err) {
      setError(asErrorMessage(err));
    }
  }

  return (
    <section>
      <div className="desk-kicker">BRIEFINGS</div>
      <h1 className="desk-title">
        <T zh="早报台" en="Briefing slate" />
      </h1>
      <p className="desk-lead">
        <T zh="新建默认 draft。付印前公开页 404。脉搏先写成 0，不要用簇数回填。" en="New days start as drafts. Pulse starts at zero; never backfill from story counts." />
      </p>
      {error ? <Banner kind="error">{error}</Banner> : null}
      {ok ? <Banner kind="ok">{ok}</Banner> : null}

      <form className="desk-panel desk-form" onSubmit={create}>
        <h2>
          <T zh="开一天草稿" en="Open a draft day" />
        </h2>
        <div className="desk-grid two">
          <Field label="date">
            <input type="date" value={date} onChange={(e) => setDate(e.currentTarget.value)} required />
          </Field>
          <Field label="updatedAt">
            <input value={updatedAt} onChange={(e) => setUpdatedAt(e.currentTarget.value)} placeholder="07:00" required />
          </Field>
        </div>
        <TextPair label="title" value={title} onChange={setTitle} />
        <TextPair label="moreHeading" value={moreHeading} onChange={setMoreHeading} />
        <TextPair label="lede[0]" value={lede} onChange={setLede} multiline />
        <button className="desk-btn primary" type="submit">
          <T zh="创建草稿" en="Create draft" />
        </button>
      </form>

      <table className="desk-table">
        <thead>
          <tr>
            <th>date</th>
            <th>
              <T zh="标题" en="Title" />
            </th>
            <th>must</th>
            <th>pulse</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.date}>
              <td className="desk-mono">{item.date}</td>
              <td>
                <Stamp status={item.status} /> {item.title.zh}
              </td>
              <td>{item.mustReadCount}</td>
              <td>{item.clusters}</td>
              <td>
                <Link href={`/admin/briefings/${item.date}`}>
                  <T zh="划版" en="Edit" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}