import { isAdmin } from "@/lib/auth";
import { dispatchWorkflow } from "@/lib/github";

export async function POST() {
  if (!(await isAdmin())) return Response.json({ error: "Unauthorized" }, { status: 401 });
  try {
    await dispatchWorkflow();
    return Response.json({ ok: true });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Could not start update" }, { status: 409 });
  }
}
