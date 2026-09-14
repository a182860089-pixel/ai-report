export function parseISODate(iso: string) {
  const [year, month, day] = iso.split("-").map(Number);
  return { year, month, day, date: new Date(year, month - 1, day) };
}

export function weekdayText(iso: string) {
  const { date } = parseISODate(iso);
  const zh = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
  const en = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  return { zh: zh[date.getDay()], en: en[date.getDay()] };
}

export function formatLongDate(iso: string) {
  const { year, month, day } = parseISODate(iso);
  const weekday = weekdayText(iso);
  const enMonths = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
  ];
  return {
    zh: `${year}年${month}月${day}日 ${weekday.zh}`,
    en: `${weekday.en}, ${enMonths[month - 1]} ${day}, ${year}`
  };
}

export function formatMonth(iso: string) {
  const { year, month } = parseISODate(iso);
  const enMonths = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
  ];
  return {
    zh: `${year} 年 ${month} 月`,
    en: `${enMonths[month - 1]} ${year}`
  };
}

export function padNum(n: number) {
  return String(n).padStart(2, "0");
}

export function mondayFirstOffset(year: number, month: number) {
  const day = new Date(year, month - 1, 1).getDay();
  return (day + 6) % 7;
}

export function daysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate();
}

export function isoDate(year: number, month: number, day: number) {
  return `${year}-${padNum(month)}-${padNum(day)}`;
}

export function startOfWeek(iso: string) {
  const { date } = parseISODate(iso);
  const offset = (date.getDay() + 6) % 7;
  date.setDate(date.getDate() - offset);
  return isoDate(date.getFullYear(), date.getMonth() + 1, date.getDate());
}