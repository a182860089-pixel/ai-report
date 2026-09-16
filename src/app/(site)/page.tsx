import { notFound } from "next/navigation";
import { BriefingView } from "@/components/BriefingView";
import { isNotFoundError, todayBriefing } from "@/data";

export default async function HomePage() {
  try {
    const briefing = await todayBriefing();
    return <BriefingView briefing={briefing} currentDate={briefing.date} />;
  } catch (error) {
    if (isNotFoundError(error)) notFound();
    throw error;
  }
}
