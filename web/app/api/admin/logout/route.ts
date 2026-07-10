import { clearAdminSession } from "@/lib/auth";

export async function POST() {
  await clearAdminSession();
  return Response.json({ ok: true });
}
