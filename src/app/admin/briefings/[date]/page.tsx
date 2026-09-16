"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { T } from "@/components/Text";
import { Banner, ConfirmButton, Field, PairList, Stamp, TextPair, asErrorMessage } from "@/components/admin/ui";
import { adminApi, type AdminBriefing } from "@/lib/admin-api";
import type { Text } from "@/data/types";

type PulseTopicDraft = { name: Text; count: number };

export default function AdminBriefingDetailPage() {
  const params = useParams<{ date: string }>();
  const router = useRouter();
  const date = params.date;
  const [item, setItem] = useState<AdminBriefing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function reload() {
    setItem(await adminApi.briefing(date));
  }

  useEffect(() => {
    reload().catch((err) => setError(asErrorMessage(err)));
  }, [date]);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!item) return;
    setError(null);
    setOk(null);
    try {
      const saved = await adminApi.patchBriefing(date, {
        title: item.title,
        weekday: item.weekday,
        moreHeading: item.moreHeading,
        lede: item.lede,
        updatedAt: item.updatedAt,
        pulse: {
          clusters: Number(item.pulse.clusters),
          articles: Number(item.pulse.articles),
          zhEn: item.pulse.zhEn,
          healthy: Number(item.pulse.healthy),
          totalSources: Number(item.pulse.totalSources),
          topics: item.pulse.topics.map((row) => ({ name: row.name, count: Number(row.count) }))
        }
      });
      setItem(saved);
      setOk("Briefing saved. Pulse snapshot untouched by story counts.");
    } catch (err) {
      setError(asErrorMessage(err));
    }
  }

  if (!item && !error) {
    return (
      <p className="desk-hint">
        <T zh="在取稿…" en="Loading…" />
      </p>
    );
  }
  if (!item) return error ? <Banner kind="error">{error}</Banner> : null;

  const topics = item.pulse.topics as PulseTopicDraft[];

  return (
    <section>
      <div className="desk-kicker">
        {date} · <Stamp status={item.status} />
      </div>
      <h1 className="desk-title">{item.title.zh}</h1>
      <p className="desk-lead">
        <T zh="脉搏是快照。改簇不会改 clusters / totalSources。" en="Pulse is a snapshot. Editing stories will not rewrite clusters or totalSources." />
      </p>
      {error ? <Banner kind="error">{error}</Banner> : null}
      {ok ? <Banner kind="ok">{ok}</Banner> : null}

      <div className="desk-toolbar">
        {item.status === "draft" ? (
          <button
            type="button"
            className="desk-btn primary"
            onClick={async () => {
              setError(null);
              try {
                setItem(await adminApi.publish(date));
                setOk("Published.");
              } catch (err) {
                setError(asErrorMessage(err));
              }
            }}
          >
            <T zh="付印" en="Publish" />
          </button>
        ) : (
          <button
            type="button"
            className="desk-btn"
            onClick={async () => {
              setError(null);
              try {
                setItem(await adminApi.unpublish(date));
                setOk("Unpublished. Public page is 404.");
              } catch (err) {
                setError(asErrorMessage(err));
              }
            }}
          >
            <T zh="撤下" en="Unpublish" />
          </button>
        )}
        <Link className="desk-btn" href={`/d/${date}`}>
          <T zh="看公开页" en="Open public page" />
        </Link>
        <ConfirmButton
          className="desk-btn ghost danger"
          disabled={item.status === "published"}
          label={<T zh="删这一天" en="Delete day" />}
          confirm={<T zh="草稿和簇都会没" en="Draft + stories go" />}
          onConfirm={async () => {
            setError(null);
            try {
              await adminApi.deleteBriefing(date);
              router.replace("/admin/briefings");
            } catch (err) {
              setError(asErrorMessage(err));
            }
          }}
        />
      </div>

      <form className="desk-form" onSubmit={save}>
        <TextPair label="title" value={item.title} onChange={(title) => setItem({ ...item, title })} />
        <div className="desk-grid two">
          <TextPair label="weekday" value={item.weekday} onChange={(weekday) => setItem({ ...item, weekday })} />
          <Field label="updatedAt">
            <input value={item.updatedAt} onChange={(e) => setItem({ ...item, updatedAt: e.currentTarget.value })} />
          </Field>
        </div>
        <TextPair label="moreHeading" value={item.moreHeading} onChange={(moreHeading) => setItem({ ...item, moreHeading })} />
        <PairList label="lede" items={item.lede} onChange={(lede) => setItem({ ...item, lede })} />

        <div className="desk-panel desk-form">
          <h2>pulse snapshot</h2>
          <div className="desk-grid two">
            <Field label="clusters">
              <input type="number" value={item.pulse.clusters} onChange={(e) => setItem({ ...item, pulse: { ...item.pulse, clusters: Number(e.currentTarget.value) } })} />
            </Field>
            <Field label="articles">
              <input type="number" value={item.pulse.articles} onChange={(e) => setItem({ ...item, pulse: { ...item.pulse, articles: Number(e.currentTarget.value) } })} />
            </Field>
            <Field label="zhEn">
              <input value={item.pulse.zhEn} onChange={(e) => setItem({ ...item, pulse: { ...item.pulse, zhEn: e.currentTarget.value } })} />
            </Field>
            <Field label="healthy / totalSources">
              <div className="desk-toolbar">
                <input type="number" value={item.pulse.healthy} onChange={(e) => setItem({ ...item, pulse: { ...item.pulse, healthy: Number(e.currentTarget.value) } })} />
                <input type="number" value={item.pulse.totalSources} onChange={(e) => setItem({ ...item, pulse: { ...item.pulse, totalSources: Number(e.currentTarget.value) } })} />
              </div>
            </Field>
          </div>
          <div className="desk-row-head">
            <h3>pulse.topics</h3>
            <button
              type="button"
              className="desk-btn ghost"
              onClick={() => setItem({ ...item, pulse: { ...item.pulse, topics: [...topics, { name: { zh: "", en: "" }, count: 0 }] } })}
            >
              <T zh="加专题计数" en="Add topic count" />
            </button>
          </div>
          {topics.map((row, index) => (
            <div className="desk-block" key={index}>
              <TextPair
                label="name"
                value={row.name}
                onChange={(name) => {
                  const next = topics.slice();
                  next[index] = { ...row, name };
                  setItem({ ...item, pulse: { ...item.pulse, topics: next } });
                }}
              />
              <Field label="count">
                <input
                  type="number"
                  value={row.count}
                  onChange={(e) => {
                    const next = topics.slice();
                    next[index] = { ...row, count: Number(e.currentTarget.value) };
                    setItem({ ...item, pulse: { ...item.pulse, topics: next } });
                  }}
                />
              </Field>
              <button
                type="button"
                className="desk-btn ghost danger"
                onClick={() => setItem({ ...item, pulse: { ...item.pulse, topics: topics.filter((_, i) => i !== index) } })}
              >
                <T zh="删" en="Remove" />
              </button>
            </div>
          ))}
        </div>
        <button className="desk-btn primary" type="submit">
          <T zh="保存早报" en="Save briefing" />
        </button>
      </form>

      <div className="desk-row-head" style={{ marginTop: 28 }}>
        <h2>
          <T zh="当日事件簇" en="Stories this day" />
        </h2>
        <Link className="desk-btn primary" href={`/admin/stories/new?date=${date}`}>
          <T zh="新开一簇" en="New story" />
        </Link>
      </div>
      <table className="desk-table">
        <thead>
          <tr>
            <th>sec</th>
            <th>#</th>
            <th>slug</th>
            <th>
              <T zh="标题" en="Title" />
            </th>
          </tr>
        </thead>
        <tbody>
          {[...item.mustRead, ...item.more].map((story) => (
            <tr key={story.slug}>
              <td>{story.section}</td>
              <td>{story.rank ?? "—"}</td>
              <td className="desk-mono">
                <Link href={`/admin/stories/${story.slug}`}>{story.slug}</Link>
              </td>
              <td>{story.title.zh}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}