import assert from "node:assert/strict";
import test from "node:test";
import { filterRecentDailyRows, isPostedTodayOrYesterday } from "./recent-jobs.ts";

const NOW = new Date("2026-07-15T12:00:00Z");

test("keeps only today and yesterday in Berlin time", () => {
  assert.equal(isPostedTodayOrYesterday("2026-07-15", NOW), true);
  assert.equal(isPostedTodayOrYesterday("July 14, 2026", NOW), true);
  assert.equal(isPostedTodayOrYesterday("2026-07-13", NOW), false);
  assert.equal(isPostedTodayOrYesterday("", NOW), false);
});

test("handles relative job dates", () => {
  assert.equal(isPostedTodayOrYesterday("6 hours ago", NOW), true);
  assert.equal(isPostedTodayOrYesterday("1 day ago", NOW), true);
  assert.equal(isPostedTodayOrYesterday("2 days ago", NOW), false);
});

test("filters stale sheet rows even when the crawler has not refreshed", () => {
  const rows = [
    { "Posted Date": "2026-07-15", title: "Today" },
    { "Posted Date": "2026-07-14", title: "Yesterday" },
    { "Posted Date": "2026-07-13", title: "Stale" },
  ];

  assert.deepEqual(filterRecentDailyRows(rows, NOW).map((row) => row.title), ["Today", "Yesterday"]);
});
