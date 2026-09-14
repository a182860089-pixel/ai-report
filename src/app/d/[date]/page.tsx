import { notFound } from "next/navigation";
import { BriefingView } from "@/components/BriefingView";
import { getBriefing, listBriefingDates } from "@/data";

type Props = {
  params: Promise<{ date: string }>;
};

export function generateStaticParams() {
  return listBriefingDates().map((date) => ({ date }));
}

export async function generateMetadata({ params }: Props) {
  const { date } = await params;
  const briefing = getBriefing(date);
  if (!briefing) return { title: "早报" };
  return { title: briefing.title.zh };
}

export default async function DatePage({ params }: Props) {
  const { date } = await params;
  const briefing = getBriefing(date);
  if (!briefing) notFound();
  return <BriefingView briefing={briefing} />;
}