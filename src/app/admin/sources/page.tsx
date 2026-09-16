"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { T } from "@/components/Text";
import { Banner, ConfirmButton, Field, TextPair, asErrorMessage } from "@/components/admin/ui";
import { adminApi, type AdminSource } from "@/lib/admin-api";

const empty = {
  id: "",
  name: "",
  status: "ok" as AdminSource["status"],
  lastFetch: "—",
  todayCount: 0,
  consecutiveFailures: 0,
  isQuarantined: false,
  detail: { zh: "", en: "" },
  homepageUrl: "",
  feedUrl: ""
};

function payloadFrom(item: typeof empty | AdminSource) {
  return {
    id: "id" in item ? item.id : undefined,
    name: item.name,
    status: item.status,
    lastFetch: item.lastFetch || "—",
    todayCount: Number(item.todayCount),
    consecutiveFailures: Number(item.consecutiveFailures),
    isQuarantined: item.isQuarantined,
    detail: item.detail,
    homepageUrl: item.homepageUrl || null,
    feedUrl: item.feedUrl || null
  };
}

export default function AdminSourcesPage() {
  const [items, setItems] = useState<AdminSource[]>([]);
  const [draft, setDraft] = useState(empty);
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function reload() {
    setItems(await adminApi.sources());
  }

  useEffect(() => {
    reload().catch((err) => setError(asErrorMessage(err)));
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setOk(null);
    try {
      const body = payloadFrom(draft);
      await adminApi.createSource(body);
      setDraft(empty);
      setOk("Source created.");
      await reload();
    } catch (err) {
      setError(asErrorMessage(err));
    }
  }

  return (
    <section>
      <div className="desk-kicker">SOURCES</div>
      <h1 className="desk-title">
        <T zh="信源目录" en="Source catalog" />
      </h1>
      <p className="desk-lead">
        <T zh="URL 只收 https。抓取和划版去采集页。公开 JSON 仍然不带 URL。" en="HTTPS only. Fetch and cluster on the pipeline page. Public JSON still omits URLs." />{" "}
        <Link href="/admin/pipeline">
          <T zh="打开采集" en="Open pipeline" />
        </Link>
      </p>
      {error ? <Banner kind="error">{error}</Banner> : null}
      {ok ? <Banner kind="ok">{ok}</Banner> : null}

      <form className="desk-panel desk-form" onSubmit={create}>
        <h2>
          <T zh="新建" en="Create" />
        </h2>
        <div className="desk-grid two">
          <Field label="id / code">
            <input className="desk-mono" value={draft.id} onChange={(e) => setDraft({ ...draft, id: e.currentTarget.value })} required />
          </Field>
          <Field label="name">
            <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.currentTarget.value })} required />
          </Field>
          <Field label="status">
            <select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.currentTarget.value as AdminSource["status"] })}>
              <option value="ok">ok</option>
              <option value="late">late</option>
              <option value="bad">bad</option>
            </select>
          </Field>
          <Field label="lastFetch">
            <input value={draft.lastFetch} onChange={(e) => setDraft({ ...draft, lastFetch: e.currentTarget.value })} />
          </Field>
        </div>
        <TextPair label="detail" value={draft.detail} onChange={(detail) => setDraft({ ...draft, detail })} multiline />
        <Field label="homepageUrl">
          <input value={draft.homepageUrl} onChange={(e) => setDraft({ ...draft, homepageUrl: e.currentTarget.value })} placeholder="https://" />
        </Field>
        <Field label="feedUrl">
          <input value={draft.feedUrl} onChange={(e) => setDraft({ ...draft, feedUrl: e.currentTarget.value })} placeholder="https://" />
        </Field>
        <button className="desk-btn primary" type="submit">
          <T zh="入库" en="Create" />
        </button>
      </form>

      <table className="desk-table">
        <thead>
          <tr>
            <th>code</th>
            <th>
              <T zh="名称" en="Name" />
            </th>
            <th>status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td className="desk-mono">{item.id}</td>
              <td>
                {editing === item.id ? (
                  <div className="desk-stack">
                    <Field label="name">
                      <input value={item.name} onChange={(e) => setItems(items.map((row) => (row.id === item.id ? { ...row, name: e.currentTarget.value } : row)))} />
                    </Field>
                    <Field label="status">
                      <select
                        value={item.status}
                        onChange={(e) =>
                          setItems(items.map((row) => (row.id === item.id ? { ...row, status: e.currentTarget.value as AdminSource["status"] } : row)))
                        }
                      >
                        <option value="ok">ok</option>
                        <option value="late">late</option>
                        <option value="bad">bad</option>
                      </select>
                    </Field>
                    <Field label="lastFetch">
                      <input value={item.lastFetch} onChange={(e) => setItems(items.map((row) => (row.id === item.id ? { ...row, lastFetch: e.currentTarget.value } : row)))} />
                    </Field>
                    <TextPair label="detail" value={item.detail} onChange={(detail) => setItems(items.map((row) => (row.id === item.id ? { ...row, detail } : row)))} multiline />
                    <Field label="homepageUrl">
                      <input value={item.homepageUrl ?? ""} onChange={(e) => setItems(items.map((row) => (row.id === item.id ? { ...row, homepageUrl: e.currentTarget.value } : row)))} />
                    </Field>
                    <Field label="feedUrl">
                      <input value={item.feedUrl ?? ""} onChange={(e) => setItems(items.map((row) => (row.id === item.id ? { ...row, feedUrl: e.currentTarget.value } : row)))} />
                    </Field>
                    <label>
                      <input
                        type="checkbox"
                        checked={item.isQuarantined}
                        onChange={(e) => setItems(items.map((row) => (row.id === item.id ? { ...row, isQuarantined: e.currentTarget.checked } : row)))}
                      />{" "}
                      isQuarantined
                    </label>
                    <button
                      type="button"
                      className="desk-btn primary"
                      onClick={async () => {
                        setError(null);
                        try {
                          const body = payloadFrom(item);
                          delete (body as { id?: string }).id;
                          await adminApi.patchSource(item.id, body);
                          setOk("Source saved.");
                          setEditing(null);
                          await reload();
                        } catch (err) {
                          setError(asErrorMessage(err));
                        }
                      }}
                    >
                      <T zh="保存" en="Save" />
                    </button>
                  </div>
                ) : (
                  <>
                    {item.name}
                    <div className="desk-hint">
                      {item.detail.zh} · {item.lastFetch} · fail {item.consecutiveFailures}
                    </div>
                  </>
                )}
              </td>
              <td>{item.status}{item.isQuarantined ? " / Q" : ""}</td>
              <td>
                <div className="desk-toolbar">
                  <button type="button" className="desk-btn ghost" onClick={() => setEditing(item.id)}>
                    <T zh="改" en="Edit" />
                  </button>
                  <ConfirmButton
                    className="desk-btn ghost danger"
                    label={<T zh="删" en="Delete" />}
                    confirm={<T zh="确认删？" en="Confirm?" />}
                    onConfirm={async () => {
                      setError(null);
                      try {
                        await adminApi.deleteSource(item.id);
                        await reload();
                      } catch (err) {
                        setError(asErrorMessage(err));
                      }
                    }}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}