type DateParts = { year: number; month: number; day: number };

const MONTHS = new Map([
  ["jan", 1], ["feb", 2], ["mar", 3], ["apr", 4], ["may", 5], ["jun", 6],
  ["jul", 7], ["aug", 8], ["sep", 9], ["oct", 10], ["nov", 11], ["dec", 12],
]);

function berlinDateParts(value: Date): DateParts {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Berlin",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value);
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    Number(parts.find((item) => item.type === type)?.value);
  return { year: part("year"), month: part("month"), day: part("day") };
}

function dateKey(parts: DateParts): number {
  return parts.year * 10_000 + parts.month * 100 + parts.day;
}

function daysBefore(parts: DateParts, days: number): DateParts {
  return berlinDateParts(new Date(Date.UTC(parts.year, parts.month - 1, parts.day - days, 12)));
}

function postedDateParts(rawValue: string, today: DateParts): DateParts | null {
  const value = rawValue.trim();
  if (!value) return null;

  if (/^today$/i.test(value)) return today;
  if (/^yesterday$/i.test(value)) return daysBefore(today, 1);

  const relative = /^(\d+)\s+(hour|hours|day|days)\s+ago$/i.exec(value);
  if (relative) {
    const amount = Number(relative[1]);
    return daysBefore(today, relative[2].toLowerCase().startsWith("day") ? amount : 0);
  }

  const iso = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(value);
  if (iso) return { year: Number(iso[1]), month: Number(iso[2]), day: Number(iso[3]) };

  const named = /^([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})/.exec(value);
  const month = named ? MONTHS.get(named[1].slice(0, 3).toLowerCase()) : undefined;
  if (named && month) return { year: Number(named[3]), month, day: Number(named[2]) };

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : berlinDateParts(parsed);
}

export function isPostedTodayOrYesterday(value: string, now = new Date()): boolean {
  const today = berlinDateParts(now);
  const yesterday = daysBefore(today, 1);
  const posted = postedDateParts(value, today);
  if (!posted) return false;
  const postedKey = dateKey(posted);
  return postedKey === dateKey(today) || postedKey === dateKey(yesterday);
}

export function filterRecentDailyRows<T extends Record<string, string>>(rows: T[], now = new Date()): T[] {
  return rows.filter((row) => isPostedTodayOrYesterday(row["Posted Date"] ?? "", now));
}
