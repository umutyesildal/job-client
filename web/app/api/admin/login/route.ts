import { createAdminSession, verifyAdminPassword } from "@/lib/auth";

export async function POST(request: Request) {
  const payload = (await request.json().catch(() => ({}))) as { password?: string };
  if (!payload.password || !verifyAdminPassword(payload.password)) {
    return Response.json({ error: "Invalid password" }, { status: 401 });
  }
  await createAdminSession();
  return Response.json({ ok: true });
}
