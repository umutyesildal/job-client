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

const ROLE_RULES: Array<[string, RegExp]> = [
  ["Fullstack", /\b(full[- ]?stack|fullstack)\b/i],
  ["Backend", /\b(backend|back[- ]?end|api|python|java|golang|node\.?js|php|ruby|scala)\b/i],
  ["Frontend", /\b(frontend|front[- ]?end|react|next\.?js|javascript|typescript|web ui|ui engineer)\b/i],
  ["Data / AI / ML", /\b(data engineer|data scientist|machine learning|ml|ai engineer|analytics engineer|data platform|computer vision|nlp|data)\b/i],
  ["Platform / DevOps / SRE", /\b(devops|sre|site reliability|platform|cloud|infrastructure|systems?)\b/i],
  ["Security", /\b(security|application security|appsec|iam|soc)\b/i],
  ["Mobile", /\b(android|ios|mobile|react native|flutter)\b/i],
  ["QA / Test", /\b(qa|quality assurance|test automation|sdet|engineer in test)\b/i],
  ["Product", /\b(product manager|product owner|technical product manager)\b/i],
];

const LEVEL_RULES: Array<[string, RegExp]> = [
  ["Intern / Working Student", /\b(intern|internship|working student|werkstudent|praktik|praktikum|thesis student)\b/i],
  ["Junior / Entry", /\b(junior|entry[- ]?level|graduate|trainee|associate)\b/i],
  ["Staff / Principal", /\b(staff|principal|distinguished|fellow)\b/i],
  ["Lead", /\b(team lead|tech lead|lead)\b/i],
  ["Manager / Head / Director", /\b(manager|head|director|vp|chief)\b/i],
  ["Senior", /\b(senior|sr\.?)\b/i],
];

const TECH_RULES: Array<[string, RegExp]> = [
  ["JavaScript", /\bjavascript\b|\bjs\b/i], ["TypeScript", /\btypescript\b|\bts\b/i],
  ["React", /\breact(?:\.js)?\b/i], ["Next.js", /\bnext\.?js\b/i],
  ["Node.js", /\bnode\.?js\b/i], ["Python", /\bpython\b/i], ["Java", /\bjava\b/i],
  ["Go", /\bgolang\b|\bgo developer\b|\bgo engineer\b/i], ["C#", /\bc#\b|\b\.net\b/i],
  ["C++", /\bc\+\+/i], ["Ruby", /\bruby\b/i], ["PHP", /\bphp\b/i],
  ["Kotlin", /\bkotlin\b/i], ["Swift", /\bswift\b/i], ["AWS", /\baws\b|amazon web services/i],
  ["Azure", /\bazure\b/i], ["GCP", /\bgcp\b|google cloud/i], ["Kubernetes", /\bkubernetes\b|\bk8s\b/i],
  ["Docker", /\bdocker\b/i], ["Terraform", /\bterraform\b/i], ["SQL", /\bsql\b|postgres|mysql/i],
];

function splitList(raw: string): string[] {
  return raw.split(/[,;|]/).map((item) => item.trim()).filter(Boolean);
}

function classify(text: string, rules: Array<[string, RegExp]>, fallback: string): string {
  return rules.find(([, pattern]) => pattern.test(text))?.[0] ?? fallback;
}

function workMode(remote: string): string {
  const normalized = remote.trim().toLowerCase();
  if (normalized.includes("hybrid")) return "Hybrid";
  if (normalized === "yes" || normalized.includes("remote")) return "Remote";
  return "On-site";
}

function toJob(row: Record<string, string>): Job {
  const title = value(row, "Job Title");
  const department = value(row, "Department");
  const description = value(row, "Job Description");
  const searchable = `${title} ${department} ${description}`;
  const explicitKeywords = splitList(value(row, "Keywords", "Keyword"));
  const techStack = splitList(value(row, "Tech Stack", "Technology Stack"));
  const derivedTech = TECH_RULES.filter(([, pattern]) => pattern.test(searchable)).map(([name]) => name);
  const role = value(row, "Role") || classify(`${title} ${department}`, ROLE_RULES, "Other");
  const level = value(row, "Level", "Seniority") || classify(`${title} ${department}`, LEVEL_RULES, "Not specified");
  const remote = value(row, "Remote");
  return {
    company: value(row, "Company Name", "Company"),
    title,
    location: value(row, "Location"),
    link: value(row, "Job Link"),
    postedDate: value(row, "Posted Date"),
    remote,
    department,
    keywords: explicitKeywords.length ? explicitKeywords : [role, department, ...derivedTech].filter((item, index, items) => item && item !== "Other" && items.indexOf(item) === index),
    techStack: techStack.length ? techStack : derivedTech,
    level,
    role,
    workMode: workMode(remote),
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
