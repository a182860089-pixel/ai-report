import Link from "next/link";
import { T } from "@/components/Text";
import { CURRENT_DATE, getBriefing, listBriefingDates } from "@/data";
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

export default function ArchivePage() {
  const { year, month } = parseISODate(CURRENT_DATE);
  const monthText = formatMonth(CURRENT_DATE);
  const dates = new Set(listBriefingDates());
  const offset = mondayFirstOffset(year, month);
  const total = daysInMonth(year, month);
  const cells: Array<{ day: number | null; iso?: string }> = [];
  for (let i = 0; i < offset; i += 1) cells.push({ day: null });
  for (let day = 1; day <= total; day += 1) {
    cells.push({ day, iso: isoDate(year, month, day) });
  }

  const generated = listBriefingDates()
    .slice()
    .reverse()
    .map((date) => getBriefing(date))
    .filter((item): item is NonNullable<typeof item> => Boolean(item));

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
          const briefing = dates.has(cell.iso) ? getBriefing(cell.iso) : undefined;
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
              href={cell.iso === CURRENT_DATE ? "/" : `/d/${cell.iso}`}
              aria-current={cell.iso === CURRENT_DATE ? "date" : undefined}
            >
              {cell.day}
              <small>{briefing.pulse.clusters}</small>
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
            href={briefing.date === CURRENT_DATE ? "/" : `/d/${briefing.date}`}
          >
            <strong>
              <T zh={`${longDate.zh.replace(" 星期", " · 星期")} · ${briefing.title.zh}`} en={`${longDate.en} · ${briefing.title.en}`} />
            </strong>
            <span className="note">
              {briefing.mustRead.length} <T zh="必读" en="must-read" /> · {briefing.pulse.clusters}{" "}
              <T zh="事件簇" en="clusters" />
            </span>
          </Link>
        );
      })}
    </section>
  );
}