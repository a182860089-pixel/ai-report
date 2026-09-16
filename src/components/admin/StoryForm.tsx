"use client";

import { FormEvent, useEffect, useState } from "react";
import { T } from "@/components/Text";
import { Field, PairList, TextPair } from "@/components/admin/ui";
import type { AdminCitation, AdminStory, AdminTopic } from "@/lib/admin-api";
import { adminApi } from "@/lib/admin-api";
import type { Text, TimelineItem } from "@/data/types";

export type StoryDraft = {
  slug: string;
  date: string;
  topicSlug: string;
  section: "must" | "more";
  rank: number;
  title: Text;
  dek: Text;
  synthesis: Text[];
  timeline: TimelineItem[];
  sources: AdminCitation[];
};

export function blankStory(date = ""): StoryDraft {
  return {
    slug: "",
    date,
    topicSlug: "",
    section: "must",
    rank: 1,
    title: { zh: "", en: "" },
    dek: { zh: "", en: "" },
    synthesis: [{ zh: "", en: "" }],
    timeline: [{ time: "07:00", text: { zh: "", en: "" } }],
    sources: [
      {
        name: "",
        lang: "zh",
        kind: { zh: "一手", en: "Primary" },
        time: "07:00",
        sourceCode: null
      }
    ]
  };
}

export function fromAdminStory(story: AdminStory): StoryDraft {
  return {
    slug: story.slug,
    date: story.date,
    topicSlug: story.topicSlug,
    section: story.section,
    rank: story.rank ?? 1,
    title: story.title,
    dek: story.dek,
    synthesis: story.synthesis.length ? story.synthesis : [],
    timeline: story.timeline,
    sources: story.sources
  };
}

function filledText(items: Text[]) {
  return items.filter((item) => item.zh.trim() && item.en.trim());
}

export function storyPayload(draft: StoryDraft, creating: boolean) {
  const sources = draft.sources
    .filter((row) => row.name.trim() && row.kind.zh.trim() && row.kind.en.trim() && row.time.trim())
    .map((row) => ({
      name: row.name.trim(),
      lang: row.lang,
      kind: row.kind,
      time: row.time,
      sourceCode: row.sourceCode?.trim() ? row.sourceCode.trim() : null
    }));
  const body: Record<string, unknown> = {
    date: draft.date,
    topicSlug: draft.topicSlug,
    section: draft.section,
    title: draft.title,
    dek: draft.dek,
    synthesis: filledText(draft.synthesis),
    timeline: draft.timeline.filter((row) => row.time.trim() && row.text.zh.trim() && row.text.en.trim()),
    sources
  };
  if (creating) body.slug = draft.slug.trim();
  if (draft.section === "must") body.rank = Number(draft.rank);
  return body;
}

export function StoryForm({
  draft,
  creating,
  onChange,
  onSubmit,
  busy
}: {
  draft: StoryDraft;
  creating: boolean;
  onChange: (next: StoryDraft) => void;
  onSubmit: () => void | Promise<void>;
  busy?: boolean;
}) {
  const [topics, setTopics] = useState<AdminTopic[]>([]);
  const [codes, setCodes] = useState<string[]>([]);

  useEffect(() => {
    Promise.all([adminApi.topics(), adminApi.sources()]).then(([topicRows, sourceRows]) => {
      setTopics(topicRows);
      setCodes(sourceRows.map((row) => row.id));
    }).catch(() => undefined);
  }, []);

  function update<K extends keyof StoryDraft>(key: K, value: StoryDraft[K]) {
    onChange({ ...draft, [key]: value });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    await onSubmit();
  }

  return (
    <form className="desk-form" onSubmit={submit}>
      <div className="desk-grid two">
        <Field label="slug">
          <input className="desk-mono" value={draft.slug} disabled={!creating} onChange={(e) => update("slug", e.currentTarget.value)} required={creating} />
        </Field>
        <Field label="date">
          <input type="date" value={draft.date} onChange={(e) => update("date", e.currentTarget.value)} required />
        </Field>
        <Field label="topicSlug">
          <select value={draft.topicSlug} onChange={(e) => update("topicSlug", e.currentTarget.value)} required>
            <option value="">—</option>
            {topics.map((topic) => (
              <option key={topic.slug} value={topic.slug}>
                {topic.slug} · {topic.name.zh}
              </option>
            ))}
          </select>
        </Field>
        <Field label="section">
          <select value={draft.section} onChange={(e) => update("section", e.currentTarget.value as "must" | "more")}>
            <option value="must">must</option>
            <option value="more">more</option>
          </select>
        </Field>
        {draft.section === "must" ? (
          <Field label="rank">
            <input type="number" min={1} value={draft.rank} onChange={(e) => update("rank", Number(e.currentTarget.value))} required />
          </Field>
        ) : (
          <p className="desk-hint">more.rank 入库为 null</p>
        )}
      </div>
      <TextPair label="title" value={draft.title} onChange={(title) => update("title", title)} />
      <TextPair label="dek" value={draft.dek} onChange={(dek) => update("dek", dek)} multiline />
      <PairList label="synthesis" items={draft.synthesis} onChange={(synthesis) => update("synthesis", synthesis)} rows={5} />

      <div className="desk-stack">
        <div className="desk-row-head">
          <h3>timeline</h3>
          <button
            type="button"
            className="desk-btn ghost"
            onClick={() => update("timeline", [...draft.timeline, { time: "07:00", text: { zh: "", en: "" } }])}
          >
            <T zh="加节点" en="Add beat" />
          </button>
        </div>
        {draft.timeline.map((row, index) => (
          <div className="desk-block" key={index}>
            <Field label="time">
              <input value={row.time} onChange={(e) => {
                const next = draft.timeline.slice();
                next[index] = { ...row, time: e.currentTarget.value };
                update("timeline", next);
              }} />
            </Field>
            <TextPair
              label="text"
              value={row.text}
              onChange={(text) => {
                const next = draft.timeline.slice();
                next[index] = { ...row, text };
                update("timeline", next);
              }}
              multiline
            />
            <button type="button" className="desk-btn ghost danger" onClick={() => update("timeline", draft.timeline.filter((_, i) => i !== index))}>
              <T zh="删" en="Remove" />
            </button>
          </div>
        ))}
      </div>

      <div className="desk-stack">
        <div className="desk-row-head">
          <h3>citations</h3>
          <button
            type="button"
            className="desk-btn ghost"
            onClick={() =>
              update("sources", [
                ...draft.sources,
                { name: "", lang: "en", kind: { zh: "媒体", en: "Press" }, time: "07:00", sourceCode: null }
              ])
            }
          >
            <T zh="加引用" en="Add citation" />
          </button>
        </div>
        {draft.sources.map((row, index) => (
          <div className="desk-block" key={index}>
            <div className="desk-grid two">
              <Field label="name">
                <input value={row.name} onChange={(e) => {
                  const next = draft.sources.slice();
                  next[index] = { ...row, name: e.currentTarget.value };
                  update("sources", next);
                }} />
              </Field>
              <Field label="sourceCode">
                <select
                  value={row.sourceCode ?? ""}
                  onChange={(e) => {
                    const next = draft.sources.slice();
                    next[index] = { ...row, sourceCode: e.currentTarget.value || null };
                    update("sources", next);
                  }}
                >
                  <option value="">— null</option>
                  {codes.map((code) => (
                    <option key={code} value={code}>
                      {code}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="lang">
                <select
                  value={row.lang}
                  onChange={(e) => {
                    const next = draft.sources.slice();
                    next[index] = { ...row, lang: e.currentTarget.value as "zh" | "en" };
                    update("sources", next);
                  }}
                >
                  <option value="zh">zh</option>
                  <option value="en">en</option>
                </select>
              </Field>
              <Field label="time">
                <input value={row.time} onChange={(e) => {
                  const next = draft.sources.slice();
                  next[index] = { ...row, time: e.currentTarget.value };
                  update("sources", next);
                }} />
              </Field>
            </div>
            <TextPair
              label="kind"
              value={row.kind}
              onChange={(kind) => {
                const next = draft.sources.slice();
                next[index] = { ...row, kind };
                update("sources", next);
              }}
            />
            <button type="button" className="desk-btn ghost danger" onClick={() => update("sources", draft.sources.filter((_, i) => i !== index))}>
              <T zh="删" en="Remove" />
            </button>
          </div>
        ))}
      </div>

      <button className="desk-btn primary" type="submit" disabled={busy}>
        {busy ? <T zh="在写…" en="Saving…" /> : <T zh="保存簇" en="Save story" />}
      </button>
    </form>
  );
}