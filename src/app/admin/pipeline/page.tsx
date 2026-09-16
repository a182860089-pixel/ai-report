"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { T } from "@/components/Text";
import { Banner, Field, asErrorMessage } from "@/components/admin/ui";
import {
  adminApi,
  type PipelineArticle,
  type PipelineJob,
  type PipelineRun,
  type PipelineSchedule,
  type PipelineSkip
} from "@/lib/admin-api";

function shanghaiToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai" }).format(new Date());
}

function stamp(value: string | null) {
  if (!value) return "—";
  return value.replace("T", " ").replace("Z", "");
}

export default function AdminPipelinePage() {
  const [codes, setCodes] = useState("");
  const [clusterDate, setClusterDate] = useState(shanghaiToday);
  const [sourceFilter, setSourceFilter] = useState("");
  const [busy, setBusy] = useState<"fetch" | "cluster" | "tick" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [skipped, setSkipped] = useState<PipelineSkip[]>([]);
  const [articles, setArticles] = useState<PipelineArticle[]>([]);
  const [jobs, setJobs] = useState<PipelineJob[]>([]);
  const [slugs, setSlugs] = useState<string[]>([]);
  const [jobDate, setJobDate] = useState<string | null>(null);
  const [schedule, setSchedule] = useState<PipelineSchedule | null>(null);

  async function reload(source?: string) {
    const query = source ? { source } : undefined;
    const [runItems, articleItems, jobItems, scheduleData] = await Promise.all([
      adminApi.pipelineRuns(50),
      adminApi.pipelineArticles(query),
      adminApi.pipelineJobs(50),
      adminApi.pipelineSchedule()
    ]);
    setRuns(runItems);
    setArticles(articleItems);
    setJobs(jobItems);
    setSchedule(scheduleData);
  }

  useEffect(() => {
    reload().catch((err) => setError(asErrorMessage(err)));
  }, []);

  async function onFetch(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setOk(null);
    setBusy("fetch");
    try {
      const parsed = codes
        .split(/[,\s]+/)
        .map((item) => item.trim())
        .filter(Boolean);
      const data = await adminApi.fetchPipeline(parsed.length ? parsed : undefined);
      setSkipped(data.skipped);
      setOk(`Fetch ${data.runs.length} run(s), skip ${data.skipped.length}.`);
      await reload(sourceFilter.trim() || undefined);
    } catch (err) {
      setError(asErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function onCluster(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setOk(null);
    setBusy("cluster");
    try {
      const job = await adminApi.clusterPipeline(clusterDate);
      setSlugs(job.slugs ?? []);
      setJobDate(job.date);
      setOk(`Cluster ${job.date}: ${job.storyCount} stories / ${job.articleCount} articles.`);
      await reload(sourceFilter.trim() || undefined);
    } catch (err) {
      setError(asErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function onTick() {
    setError(null);
    setOk(null);
    setBusy("tick");
    try {
      const tick = await adminApi.pipelineTick();
      setSkipped([]);
      setSlugs(tick.slugs ?? []);
      setJobDate(tick.date);
      setOk(
        `Tick ${tick.trigger}: fetch ${tick.fetchRunCount}, skip ${tick.skippedCount}, cluster ${tick.clusterStatus}, stories ${tick.storyCount}.`
      );
      await reload(sourceFilter.trim() || undefined);
    } catch (err) {
      setError(asErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section>
      <div className="desk-kicker">PIPELINE</div>
      <h1 className="desk-title">
        <T zh="采集管线" en="Pipeline" />
      </h1>
      <p className="desk-lead">
        <T
          zh="每天上海 06:30 / 12:30 / 18:30 自动抓 RSS，入库后再 template 划成当天草稿簇。已付印日只抓不划。也可手动跑一轮。"
          en="Shanghai 06:30 / 12:30 / 18:30 auto-fetch RSS, ingest, then template-cluster into today's draft. Published days fetch only. Manual tick is available."
        />
      </p>
      {error ? <Banner kind="error">{error}</Banner> : null}
      {ok ? <Banner kind="ok">{ok}</Banner> : null}

      <div className="desk-panel" style={{ marginBottom: 18 }}>
        <h2>
          <T zh="定时调度" en="Schedule" />
        </h2>
        {schedule ? (
          <>
            <p className="desk-hint">
              <T zh="状态" en="Status" />: {schedule.enabled ? <T zh="已开启" en="on" /> : <T zh="未开启" en="off" />}
              {" · "}
              {schedule.times.join(" / ")} {schedule.timezone}
              {" · "}
              <T zh="自动划版" en="auto cluster" />: {schedule.autoCluster ? "on" : "off"}
              {" · "}
              <T zh="下一轮" en="next" />: {stamp(schedule.nextRunAt)}
            </p>
            {schedule.lastTick ? (
              <p className="desk-hint">
                <T zh="上一轮" en="last tick" />: {schedule.lastTick.trigger} / cluster {schedule.lastTick.clusterStatus} /{" "}
                {stamp(schedule.lastTick.finishedAt)}
              </p>
            ) : (
              <p className="desk-hint">
                <T zh="还没有跑过定时轮次。" en="No scheduled tick yet." />
              </p>
            )}
            <button className="desk-btn primary" type="button" onClick={onTick} disabled={busy !== null}>
              {busy === "tick" ? <T zh="进行中…" en="Running…" /> : <T zh="立即跑一轮（抓取+划版）" en="Run fetch + cluster now" />}
            </button>
          </>
        ) : (
          <p className="desk-hint">
            <T zh="正在读取调度配置…" en="Loading schedule…" />
          </p>
        )}
      </div>

      <div className="desk-panels">
        <form className="desk-panel desk-form" onSubmit={onFetch}>
          <h2>
            <T zh="抓取" en="Fetch" />
          </h2>
          <Field
            label="codes"
            hint={<T zh="信源 code，逗号分隔；空则抓全部有 feed 的源" en="Comma-separated source codes. Empty fetches every source with a feed." />}
          >
            <input
              className="desk-mono"
              value={codes}
              onChange={(event) => setCodes(event.currentTarget.value)}
              placeholder="openai-blog, hf"
            />
          </Field>
          <button className="desk-btn primary" type="submit" disabled={busy !== null}>
            {busy === "fetch" ? <T zh="进行中…" en="Fetching…" /> : <T zh="抓取" en="Fetch" />}
          </button>
        </form>

        <form className="desk-panel desk-form" onSubmit={onCluster}>
          <h2>
            <T zh="划版" en="Cluster" />
          </h2>
          <Field label={<T zh="划版日" en="Cluster date" />}>
            <input
              className="desk-mono"
              type="date"
              value={clusterDate}
              onChange={(event) => setClusterDate(event.currentTarget.value)}
              required
            />
          </Field>
          <button className="desk-btn primary" type="submit" disabled={busy !== null}>
            {busy === "cluster" ? <T zh="进行中…" en="Clustering…" /> : <T zh="划版" en="Cluster" />}
          </button>
          {slugs.length ? (
            <p className="desk-hint">
              <T zh="草稿簇" en="Draft clusters" />:{" "}
              {slugs.map((slug) => (
                <span key={slug}>
                  <Link className="desk-mono" href={`/admin/stories/${slug}`}>
                    {slug}
                  </Link>{" "}
                </span>
              ))}
              {jobDate ? (
                <Link href={`/admin/briefings/${jobDate}`}>
                  <T zh="打开早报" en="Open briefing" />
                </Link>
              ) : null}
            </p>
          ) : null}
        </form>
      </div>

      {skipped.length ? (
        <div className="desk-panel" style={{ marginTop: 18 }}>
          <h2>
            <T zh="最近跳过" en="Last skipped" />
          </h2>
          <table className="desk-table">
            <thead>
              <tr>
                <th>code</th>
                <th>reason</th>
              </tr>
            </thead>
            <tbody>
              {skipped.map((row) => (
                <tr key={`${row.code}-${row.reason}`}>
                  <td className="desk-mono">{row.code}</td>
                  <td className="desk-mono">{row.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div className="desk-row-head" style={{ marginTop: 28 }}>
        <h2>
          <T zh="抓取记录" en="Fetch runs" />
        </h2>
        <button
          type="button"
          className="desk-btn ghost"
          onClick={() => {
            setError(null);
            reload(sourceFilter.trim() || undefined).catch((err) => setError(asErrorMessage(err)));
          }}
        >
          <T zh="刷新" en="Reload" />
        </button>
      </div>
      <table className="desk-table">
        <thead>
          <tr>
            <th>source</th>
            <th>status</th>
            <th>articles</th>
            <th>started</th>
            <th>error</th>
          </tr>
        </thead>
        <tbody>
          {runs.length === 0 ? (
            <tr>
              <td colSpan={5} className="desk-hint">
                <T zh="还没有抓取记录。" en="No fetch runs yet." />
              </td>
            </tr>
          ) : (
            runs.map((row) => (
              <tr key={`${row.sourceCode}-${row.startedAt}`}>
                <td className="desk-mono">{row.sourceCode}</td>
                <td>{row.status}</td>
                <td>{row.articleCount}</td>
                <td className="desk-mono">{stamp(row.startedAt)}</td>
                <td className="desk-mono">{row.errorCode || "—"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      <div className="desk-row-head" style={{ marginTop: 28 }}>
        <h2>
          <T zh="文章" en="Articles" />
        </h2>
        <form
          className="desk-toolbar"
          onSubmit={(event) => {
            event.preventDefault();
            setError(null);
            reload(sourceFilter.trim() || undefined).catch((err) => setError(asErrorMessage(err)));
          }}
        >
          <input
            className="desk-mono"
            value={sourceFilter}
            onChange={(event) => setSourceFilter(event.currentTarget.value)}
            placeholder="openai-blog"
          />
          <button className="desk-btn ghost" type="submit">
            <T zh="筛选" en="Filter" />
          </button>
        </form>
      </div>
      <table className="desk-table">
        <thead>
          <tr>
            <th>source</th>
            <th>title</th>
            <th>lang</th>
            <th>clustered</th>
            <th>fetched</th>
          </tr>
        </thead>
        <tbody>
          {articles.length === 0 ? (
            <tr>
              <td colSpan={5} className="desk-hint">
                <T zh="还没有文章。" en="No articles yet." />
              </td>
            </tr>
          ) : (
            articles.map((row) => (
              <tr key={`${row.sourceCode}-${row.guid}`}>
                <td className="desk-mono">{row.sourceCode}</td>
                <td>
                  <a href={row.canonicalUrl} target="_blank" rel="noreferrer">
                    {row.title}
                  </a>
                </td>
                <td>{row.lang}</td>
                <td>{row.clustered ? <T zh="已划" en="yes" /> : <T zh="未划" en="no" />}</td>
                <td className="desk-mono">{stamp(row.fetchedAt)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      <h2 style={{ marginTop: 28 }}>
        <T zh="划版任务" en="Cluster jobs" />
      </h2>
      <table className="desk-table">
        <thead>
          <tr>
            <th>date</th>
            <th>status</th>
            <th>writer</th>
            <th>stories</th>
            <th>articles</th>
            <th>created</th>
          </tr>
        </thead>
        <tbody>
          {jobs.length === 0 ? (
            <tr>
              <td colSpan={6} className="desk-hint">
                <T zh="还没有划版任务。" en="No cluster jobs yet." />
              </td>
            </tr>
          ) : (
            jobs.map((row) => (
              <tr key={`${row.date}-${row.createdAt}`}>
                <td className="desk-mono">
                  <Link href={`/admin/briefings/${row.date}`}>{row.date}</Link>
                </td>
                <td>{row.status}</td>
                <td>{row.writer}</td>
                <td>{row.storyCount}</td>
                <td>{row.articleCount}</td>
                <td className="desk-mono">{stamp(row.createdAt)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </section>
  );
}
