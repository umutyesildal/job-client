import assert from "node:assert/strict";
import test from "node:test";
import { getSampleJobsSnapshot } from "./sample-data.ts";

test("sample mode always contains current rolling dates", () => {
  const snapshot = getSampleJobsSnapshot();
  const today = new Date().toISOString().slice(0, 10);
  assert.equal(snapshot.all[0]?.postedDate, today);
  assert.equal(snapshot.daily.length, 3);
});
