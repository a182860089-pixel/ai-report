"use client";

import { FormEvent, useEffect, useState } from "react";
import { T } from "@/components/Text";
import { Banner, ConfirmButton, Field, TextPair, asErrorMessage } from "@/components/admin/ui";
import { adminApi, type AdminTopic } from "@/lib/admin-api";

const empty = {
  slug: "",
  name: { zh: "", en: "" },
  blurb: { zh: "", en: "" },
  sortOrder: 0
};

export default function AdminTopicsPage() {
  const [items, setItems] = useState<AdminTopic[]>([]);
  const [draft, setDraft] = useState(empty);
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function reload() {
    setItems(await adminApi.topics());
  }

  useEffect(() => {
    reload().catch((err) => setError(asErrorMessage(err)));
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setOk(null);
    try {
      await adminApi.createTopic({
        slug: draft.slug.trim(),
        name: draft.name,
        blurb: draft.blurb,
        sortOrder: Number(draft.sortOrder)
      });
      setDraft(empty);
      setOk("Topic created.");
      await reload();
    } catch (err) {
      setError(asErrorMessage(err));
    }
  }

  async function save(item: AdminTopic) {
    setError(null);
    setOk(null);
    try {
      await adminApi.patchTopic(item.slug, {
        name: item.name,
        blurb: item.blurb,
        sortOrder: Number(item.sortOrder),
        isActive: item.isActive
      });
      setOk("Topic saved.");
      setEditing(null);
      await reload();
    } catch (err) {
      setError(asErrorMessage(err));
    }
  }

  return (
    <section>
      <div className="desk-kicker">TOPICS</div>
      <h1 className="desk-title">
        <T zh="专题目录" en="Topic catalog" />
      </h1>
      <p className="desk-lead">
        <T zh="slug 创建后不能改。有簇的专题只能下架，不能删。" en="Slug is immutable. Topics with stories can only be deactivated." />
      </p>
      {error ? <Banner kind="error">{error}</Banner> : null}
      {ok ? <Banner kind="ok">{ok}</Banner> : null}

      <form className="desk-panel desk-form" onSubmit={create}>
        <h2>
          <T zh="新建" en="Create" />
        </h2>
        <Field label="slug">
          <input className="desk-mono" value={draft.slug} onChange={(e) => setDraft({ ...draft, slug: e.currentTarget.value })} required />
        </Field>
        <TextPair label="name" value={draft.name} onChange={(name) => setDraft({ ...draft, name })} />
        <TextPair label="blurb" value={draft.blurb} onChange={(blurb) => setDraft({ ...draft, blurb })} multiline />
        <Field label="sortOrder">
          <input type="number" value={draft.sortOrder} onChange={(e) => setDraft({ ...draft, sortOrder: Number(e.currentTarget.value) })} />
        </Field>
        <button className="desk-btn primary" type="submit">
          <T zh="入库" en="Create" />
        </button>
      </form>

      <table className="desk-table">
        <thead>
          <tr>
            <th>slug</th>
            <th>
              <T zh="名称" en="Name" />
            </th>
            <th>n</th>
            <th>on</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.slug}>
              <td className="desk-mono">{item.slug}</td>
              <td>
                {editing === item.slug ? (
                  <div className="desk-stack">
                    <TextPair label="name" value={item.name} onChange={(name) => setItems(items.map((row) => (row.slug === item.slug ? { ...row, name } : row)))} />
                    <TextPair label="blurb" value={item.blurb} onChange={(blurb) => setItems(items.map((row) => (row.slug === item.slug ? { ...row, blurb } : row)))} multiline />
                    <Field label="sortOrder">
                      <input
                        type="number"
                        value={item.sortOrder}
                        onChange={(e) =>
                          setItems(items.map((row) => (row.slug === item.slug ? { ...row, sortOrder: Number(e.currentTarget.value) } : row)))
                        }
                      />
                    </Field>
                    <label>
                      <input
                        type="checkbox"
                        checked={item.isActive}
                        onChange={(e) =>
                          setItems(items.map((row) => (row.slug === item.slug ? { ...row, isActive: e.currentTarget.checked } : row)))
                        }
                      />{" "}
                      isActive
                    </label>
                    <button type="button" className="desk-btn primary" onClick={() => save(item)}>
                      <T zh="保存" en="Save" />
                    </button>
                  </div>
                ) : (
                  <>
                    {item.name.zh}
                    <div className="desk-hint">{item.blurb.zh}</div>
                  </>
                )}
              </td>
              <td>{item.clusterCount}</td>
              <td>{item.isActive ? "yes" : "off"}</td>
              <td>
                <div className="desk-toolbar">
                  <button type="button" className="desk-btn ghost" onClick={() => setEditing(item.slug)}>
                    <T zh="改" en="Edit" />
                  </button>
                  <ConfirmButton
                    className="desk-btn ghost danger"
                    label={<T zh="删" en="Delete" />}
                    confirm={<T zh="确认删？" en="Confirm?" />}
                    onConfirm={async () => {
                      setError(null);
                      try {
                        await adminApi.deleteTopic(item.slug);
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