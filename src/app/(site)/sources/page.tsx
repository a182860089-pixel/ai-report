import { T } from "@/components/Text";
import { listSources } from "@/data";

export const metadata = { title: "信源" };

const STATUS = {
  ok: { zh: "正常", en: "Healthy", className: "ok" },
  late: { zh: "延迟", en: "Late", className: "late" },
  bad: { zh: "失败", en: "Failed", className: "bad" }
} as const;

export default async function SourcesPage() {
  const sources = await listSources();
  return (
    <section>
      <div className="kicker">SOURCES</div>
      <h1 className="display">
        <T zh="信源健康" en="Source health" />
      </h1>
      <p className="date-line">
        <T zh="抓取失败不进早报。延迟超过 2 小时标橙，连续失败标红。" en="Failed fetches never enter the briefing. Late by 2 hours is amber. Repeated failure is red." />
      </p>
      <div className="card-grid">
        {sources.map((source) => {
          const status = STATUS[source.status];
          return (
            <article className="source-card" key={source.id}>
              <b>{source.name}</b>
              <p className={`note ${status.className}`}>
                <T zh={source.detail.zh} en={source.detail.en} />
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
