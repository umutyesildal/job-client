type WorkflowRun = {
  id: number;
  status: "queued" | "in_progress" | "completed";
  conclusion: string | null;
  html_url: string;
  created_at: string;
  updated_at: string;
};

function env(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing environment variable: ${name}`);
  return value;
}

async function github(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`https://api.github.com${path}`, {
    ...init,
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env("GITHUB_ACTIONS_TOKEN")}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      ...init.headers,
    },
    cache: "no-store",
  });
}

function workflowPath(): string {
  return `/repos/${env("GITHUB_OWNER")}/${env("GITHUB_REPO")}/actions/workflows/${env("GITHUB_WORKFLOW_ID")}`;
}

export async function latestWorkflowRun(): Promise<WorkflowRun | null> {
  const response = await github(`${workflowPath()}/runs?per_page=1`);
  if (!response.ok) throw new Error(`GitHub status failed: ${response.status}`);
  const payload = (await response.json()) as { workflow_runs: WorkflowRun[] };
  return payload.workflow_runs[0] ?? null;
}

export async function dispatchWorkflow(): Promise<void> {
  const current = await latestWorkflowRun();
  if (current && current.status !== "completed") throw new Error("A daily update is already running");
  const response = await github(`${workflowPath()}/dispatches`, {
    method: "POST",
    body: JSON.stringify({ ref: "main" }),
  });
  if (!response.ok) throw new Error(`GitHub dispatch failed: ${response.status}`);
}

export async function workflowStatus() {
  const run = await latestWorkflowRun();
  if (!run) return { run: null, progress: 0, step: "No runs yet" };
  if (run.status === "completed") {
    return { run, progress: 100, step: run.conclusion === "success" ? "Update complete" : "Update failed" };
  }

  const response = await github(`/repos/${env("GITHUB_OWNER")}/${env("GITHUB_REPO")}/actions/runs/${run.id}/jobs`);
  if (!response.ok) return { run, progress: run.status === "queued" ? 5 : 15, step: run.status };
  const payload = (await response.json()) as {
    jobs: Array<{ steps?: Array<{ name: string; status: string; conclusion: string | null }> }>;
  };
  const steps = payload.jobs.flatMap((job) => job.steps ?? []);
  const completed = steps.filter((step) => step.status === "completed").length;
  const active = steps.find((step) => step.status === "in_progress");
  const progress = steps.length ? Math.max(5, Math.round((completed / steps.length) * 95)) : 10;
  return { run, progress, step: active?.name ?? (run.status === "queued" ? "Waiting for runner" : "Starting") };
}
