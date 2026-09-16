import Link from "next/link";
import { notFound } from "next/navigation";
import { T } from "@/components/Text";
import { getTopic } from "@/data";
import { formatLongDate } from "@/lib/dates";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props) {
  const { slug } = await params;
  const topic = await getTopic(slug);
  return { title: topic?.name.zh ?? "专题" };
}

export default async function TopicPage({ params }: Props) {
  const { slug } = await params;
  const topic = await getTopic(slug);
  if (!topic) notFound();
  const list = topic.stories;

  return (
    <section>
      <div className="kicker">TOPIC</div>
      <h1 className="display">
        <T zh={topic.name.zh} en={topic.name.en} />
      </h1>
      <p className="date-line">
        <T zh={topic.blurb.zh} en={topic.blurb.en} />
      </p>
      {list.length === 0 ? (
        <p className="empty">
          <T zh="这个专题还没有事件簇。" en="No clusters in this topic yet." />
        </p>
      ) : (
        list.map((story) => {
          const date = formatLongDate(story.date);
          return (
            <Link key={story.slug} className="mini press" href={`/story/${story.slug}`}>
              <strong>
                <T zh={story.title.zh} en={story.title.en} />
              </strong>
              <span className="note">
                <T zh={date.zh} en={date.en} /> · {story.sourceCount} <T zh="信源" en="sources" />
              </span>
            </Link>
          );
        })
      )}
    </section>
  );
}
