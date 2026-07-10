import { JWT } from "google-auth-library";
import type { Job, JobsSnapshot } from "./jobs";

type ServiceAccount = {
  client_email: string;
  private_key: string;
};

function requiredEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing environment variable: ${name}`);
  return value;
}

function serviceAccount(): ServiceAccount {
  const parsed = JSON.parse(requiredEnv("GOOGLE_SERVICE_ACCOUNT_JSON")) as ServiceAccount;
  if (!parsed.client_email || !parsed.private_key) {
    throw new Error("GOOGLE_SERVICE_ACCOUNT_JSON is not a valid service account");
  }
  return { ...parsed, private_key: parsed.private_key.replace(/\\n/g, "\n") };
}

async function sheetRows(worksheet: string): Promise<Record<string, string>[]> {
  const credentials = serviceAccount();
  const auth = new JWT({
    email: credentials.client_email,
    key: credentials.private_key,
    scopes: ["https://www.googleapis.com/auth/spreadsheets.readonly"],
  });
  const headers = await auth.getRequestHeaders();
  const sheetId = requiredEnv("GOOGLE_SHEET_ID");
  const range = encodeURIComponent(worksheet);
  const response = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${sheetId}/values/${range}`,
    { headers, cache: "no-store" },
  );
  if (!response.ok) throw new Error(`Sheets read failed for ${worksheet}: ${response.status}`);

  const payload = (await response.json()) as { values?: string[][] };
  const [header = [], ...rows] = payload.values ?? [];
  return rows.map((row) =>
    Object.fromEntries(header.map((column, index) => [column, row[index] ?? ""])),
  );
}

function value(row: Record<string, string>, ...keys: string[]): string {
  return keys.map((key) => row[key]?.trim()).find(Boolean) ?? "";
}

function toJob(row: Record<string, string>): Job {
  return {
    company: value(row, "Company Name", "Company"),
    title: value(row, "Job Title"),
    location: value(row, "Location"),
    link: value(row, "Job Link"),
    postedDate: value(row, "Posted Date"),
    remote: value(row, "Remote"),
    department: value(row, "Department"),
  };
}

export async function getJobsSnapshot(): Promise<JobsSnapshot> {
  const [allRows, dailyRows] = await Promise.all([
    sheetRows("All Jobs"),
    sheetRows("Daily New Jobs"),
  ]);
  return {
    all: allRows.map(toJob),
    daily: dailyRows.map(toJob),
    updatedAt: new Date().toISOString(),
  };
}
