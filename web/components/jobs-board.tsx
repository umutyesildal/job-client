"use client";

import { useMemo, useState } from "react";
import type { Job, JobsSnapshot } from "@/lib/jobs";

function jobDate(value: string): string {
  const parsed = new Date(value);
  if (!value || Number.isNaN(parsed.getTime())) return value || "Unknown";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(parsed);
}

export function JobsBoard({ snapshot }: { snapshot: JobsSnapshot }) {
  const [source, setSource] = useState<"all" | "daily">("all");
  const [query, setQuery] = useState("");
  const jobs = source === "all" ? snapshot.all : snapshot.daily;
  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return jobs.filter((job) =>
      !needle || [job.title, job.company, job.location, job.department]
        .join(" ").toLocaleLowerCase().includes(needle),
    );
  }, [jobs, query]);

  return (
    <main className="page-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">Berlin Software Jobs</span>
          <h1>Daily Berlin Jobs</h1>
        </div>
        <a className="admin-link" href="/admin">Admin</a>
      </header>

      <section className="hero">
        <span className="eyebrow">Updated from Google Sheets</span>
        <h2>Find current software roles across Berlin.</h2>
        <p>One clean board, refreshed daily from company career pages and LinkedIn.</p>
      </section>

      <section className="controls">
        <div className="tabs">
          <button className={source === "all" ? "active" : ""} onClick={() => setSource("all")}>
            All Jobs <b>{snapshot.all.length}</b>
          </button>
          <button className={source === "daily" ? "active" : ""} onClick={() => setSource("daily")}>
            New Today <b>{snapshot.daily.length}</b>
          </button>
        </div>
        <input
          aria-label="Search jobs"
          placeholder="Search role, company, or location"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </section>

      <div className="jobs-table">
        <div className="table-head"><span>Role</span><span>Company</span><span>Location</span><span>Date</span></div>
        {filtered.map((job: Job, index) => (
          <a className="job-row" href={job.link || undefined} target="_blank" rel="noreferrer" key={`${job.link}-${index}`}>
            <strong>{job.title || "Untitled role"}</strong>
            <span>{job.company || "Unknown company"}</span>
            <span>{job.location || "Berlin"}</span>
            <time>{jobDate(job.postedDate)}</time>
          </a>
        ))}
        {!filtered.length && <p className="empty">No jobs match this search.</p>}
      </div>
    </main>
  );
}
