import Link from "next/link";
import { T } from "@/components/Text";
import { getMeta, listBriefings } from "@/data";
import { daysInMonth, formatLongDate, formatMonth, isoDate, mondayFirstOffset, parseISODate } from "@/lib/dates";

export const metadata = { title: "归档" };

const WEEKDAYS = [
  { zh: "一", en: "Mon" },
  { zh: "二", en: "Tue" },
  { zh: "三", en: "Wed" },
  { zh: "四", en: "Thu" },
  { zh: "五", en: "Fri" },
  { zh: "六", en: "Sat" },
  { zh: "日", en: "Sun" }
];

export default async function ArchivePage() {
  const meta = await getMeta();
  const currentDate = meta.currentDate;
  const { year, month } = parseISODate(currentDate);
  const monthText = formatMonth(currentDate);
  const from = isoDate(year, month, 1);
  const to = isoDate(year, month, daysInMonth(year, month));
  const items = await listBriefings(from, to);
  const byDate = new Map(items.map((item) => [item.date, item]));
  const offset = mondayFirstOffset(year, month);
  const total = daysInMonth(year, month);
  const cells: Array<{ day: number | null; iso?: string }> = [];
  for (let i = 0; i < offset; i += 1) cells.push({ day: null });
  for (let day = 1; day <= total; day += 1) {
    cells.push({ day, iso: isoDate(year, month, day) });
  }

  const generated = items.slice().reverse();

  return (
    <section>
      <div className="kicker">ARCHIVE</div>
      <h1 className="display">
        <T zh={monthText.zh} en={monthText.en} />
      </h1>
      <p className="date-line">
        <T zh="点日期看当天早报。空心日表示采集不足，未生成。" en="Open a day to read that briefing. Empty days were not generated." />
      </p>
      <div className="cal" aria-label="September archive">
        {WEEKDAYS.map((day) => (
          <span className="cal-label" key={day.en}>
            <T zh={day.zh} en={day.en} />
          </span>
        ))}
        {cells.map((cell, index) => {
          if (!cell.day || !cell.iso) {
            return <span className="cal-empty" key={`pad-${index}`} />;
          }
          const briefing = byDate.get(cell.iso);
          if (!briefing) {
            return (
              <span className="cal-empty" key={cell.iso}>
                {cell.day}
              </span>
            );
          }
          return (
            <Link
              key={cell.iso}
              className="day press"
              href={cell.iso === currentDate ? "/" : `/d/${cell.iso}`}
              aria-current={cell.iso === currentDate ? "date" : undefined}
            >
              {cell.day}
              <small>{briefing.clusters}</small>
            </Link>
          );
        })}
      </div>
      <h2 className="h2">
        <T zh="已生成" en="Generated" />
      </h2>
      {generated.map((briefing) => {
        const longDate = formatLongDate(briefing.date);
        return (
          <Link
            key={briefing.date}
            className="mini press"
            href={briefing.date === currentDate ? "/" : `/d/${briefing.date}`}
          >
            <strong>
              <T zh={`${longDate.zh.replace(" 星期", " · 星期")} · ${briefing.title.zh}`} en={`${longDate.en} · ${briefing.title.en}`} />
            </strong>
            <span className="note">
              {briefing.mustReadCount} <T zh="必读" en="must-read" /> · {briefing.clusters}{" "}
              <T zh="事件簇" en="clusters" />
            </span>
          </Link>
        );
      })}
    </section>
  );
}
