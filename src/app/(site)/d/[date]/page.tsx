import { notFound } from "next/navigation";
import { BriefingView } from "@/components/BriefingView";
import { getBriefing, getMeta } from "@/data";

type Props = {
  params: Promise<{ date: string }>;
};

export async function generateMetadata({ params }: Props) {
  const { date } = await params;
  const briefing = await getBriefing(date);
  if (!briefing) return { title: "早报" };
  return { title: briefing.title.zh };
}

export default async function DatePage({ params }: Props) {
  const { date } = await params;
  const [briefing, meta] = await Promise.all([getBriefing(date), getMeta()]);
  if (!briefing) notFound();
  return <BriefingView briefing={briefing} currentDate={meta.currentDate} />;
}
