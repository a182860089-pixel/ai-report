import { BriefingView } from "@/components/BriefingView";
import { todayBriefing } from "@/data";

export default function HomePage() {
  return <BriefingView briefing={todayBriefing()} />;
}