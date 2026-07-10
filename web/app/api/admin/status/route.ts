import { isAdmin } from "@/lib/auth";
import { workflowStatus } from "@/lib/github";

export async function GET() {
  if (!(await isAdmin())) return Response.json({ error: "Unauthorized" }, { status: 401 });
  try {
    return Response.json(await workflowStatus());
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Could not load status" }, { status: 502 });
  }
}
