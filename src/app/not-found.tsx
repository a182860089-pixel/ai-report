import Link from "next/link";
import { T } from "@/components/Text";

export default function NotFound() {
  return (
    <section>
      <div className="kicker">MISSING</div>
      <h1 className="display">
        <T zh="这一天还没出报" en="No briefing for this page" />
      </h1>
      <p className="date-line">
        <T zh="空日、未知簇或错链都会落到这里。" en="Empty days, unknown clusters, and bad links land here." />
      </p>
      <Link className="back press" href="/">
        <T zh="返回今日早报" en="Back to today’s briefing" />
      </Link>
    </section>
  );
}