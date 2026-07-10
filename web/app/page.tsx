import { JobsBoard } from "@/components/jobs-board";
import { getJobsSnapshot } from "@/lib/sheets";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export default async function HomePage() {
  const snapshot = await getJobsSnapshot();
  return <JobsBoard snapshot={snapshot} />;
}
