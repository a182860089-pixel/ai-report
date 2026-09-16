import Link from "next/link";
import { T } from "@/components/Text";
import { listTopics } from "@/data";

export const metadata = { title: "专题" };

export default async function TopicsPage() {
  const topics = await listTopics();
  return (
    <section>
      <div className="kicker">TOPICS</div>
      <h1 className="display">
        <T zh="按专题读，不按网站刷" en="Read by topic, not by website" />
      </h1>
      <p className="date-line">
        <T zh="同一事件会归到一个专题。专题页吃的是簇，不是原文列表。" en="One event becomes one cluster. Topic pages eat clusters, not raw article dumps." />
      </p>
      <div className="card-grid">
        {topics.map((topic) => (
          <Link key={topic.slug} className="topic-card press" href={`/topics/${topic.slug}`}>
            <b>
              <T zh={topic.name.zh} en={topic.name.en} />
            </b>
            <p className="note">
              <T zh={topic.blurb.zh} en={topic.blurb.en} />
            </p>
            <p className="note">
              {topic.clusterCount} <T zh="条事件簇" en="clusters" />
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
