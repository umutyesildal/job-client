const state = {
  source: "daily",
  settings: null,
  jobs: [],
  sortBy: "rank",
  sortAsc: false,
};

const sourceLabels = {
  related: "Best Fit",
  daily: "New Today",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function debounce(fn, wait = 180) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function formatDate(value) {
  if (!value) return "No local data yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatJobDate(value) {
  if (!value) return "";
  const valStr = String(value).trim();
  if (valStr.includes("ago") || valStr.includes("hour") || valStr.includes("day") || valStr.includes("week")) {
    return valStr;
  }
  const date = new Date(valStr);
  if (Number.isNaN(date.getTime())) return valStr;
  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function compactText(value, maxLength = 150) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1)}…`;
}

function renderSummary(summary) {
  const sources = summary.sources || {};
  $("#relatedCount").textContent = sources.related?.count ?? 0;
  $("#dailyCount").textContent = sources.daily?.count ?? 0;

  const activeSource = sources[state.source];
  $("#updatedText").textContent = `${sourceLabels[state.source]} · ${activeSource?.count ?? 0} roles · ${formatDate(activeSource?.updatedAt)}`;

  fillSettings(summary.settings);
}

function fillSettings(settings) {
  if (!settings || state.settings) return;
  state.settings = settings;
  $("#includeLinkedInInput").checked = true;
  $("#profileFitOnlyInput").checked = true;
  $("#skipUploadInput").checked = Boolean(settings.skipUpload);
  $("#limitInput").value = 25;
  $("#hoursInput").value = 24;
}

function queryParams() {
  const params = new URLSearchParams();
  params.set("source", state.source);
  params.set("q", $("#searchInput").value.trim());
  params.set("role", $("#roleSelect").value);
  params.set("remote", $("#remoteSelect").value);
  return params;
}

async function loadJobs() {
  const payload = await api(`/api/jobs?${queryParams().toString()}`);
  state.jobs = (payload.jobs || []).map((job, idx) => ({
    ...job,
    originalRank: idx + 1
  }));
  renderJobs(state.jobs);
}

function updateHeaderSortIndicators() {
  const headers = {
    rank: ".col-rank",
    title: ".col-title",
    company: ".col-company",
    mode: ".col-mode",
    date: ".col-date"
  };
  
  Object.entries(headers).forEach(([key, selector]) => {
    const el = $(selector);
    if (!el) return;
    let text = el.textContent.replace(/ [↑↓]$/, "");
    if (state.sortBy === key) {
      text += state.sortAsc ? " ↑" : " ↓";
      el.classList.add("active-sort");
    } else {
      el.classList.remove("active-sort");
    }
    el.textContent = text;
  });
}

function renderJobs(jobs) {
  const list = $("#jobsList");
  if (!jobs || !jobs.length) {
    list.innerHTML = `<div class="empty-state">No roles match these filters yet.</div>`;
    return;
  }

  updateHeaderSortIndicators();

  // Create a copy to avoid mutating the original fetched array
  const sortedJobs = [...jobs];
  console.log("Sorting jobs. Count:", sortedJobs.length, "SortBy:", state.sortBy, "Asc:", state.sortAsc);
  sortedJobs.sort((a, b) => {
    let valA, valB;
    if (state.sortBy === "rank") {
      valA = a.fitScore ?? 0;
      valB = b.fitScore ?? 0;
      return state.sortAsc ? valA - valB : valB - valA;
    } else if (state.sortBy === "title") {
      valA = (a.title || "").toLowerCase();
      valB = (b.title || "").toLowerCase();
    } else if (state.sortBy === "company") {
      valA = (a.company || "").toLowerCase();
      valB = (b.company || "").toLowerCase();
    } else if (state.sortBy === "mode") {
      valA = (a.remote || "").toLowerCase();
      valB = (b.remote || "").toLowerCase();
    } else if (state.sortBy === "date") {
      valA = a.postedDate ? new Date(a.postedDate) : new Date(0);
      valB = b.postedDate ? new Date(b.postedDate) : new Date(0);
    }
    
    if (valA < valB) return state.sortAsc ? -1 : 1;
    if (valA > valB) return state.sortAsc ? 1 : -1;
    return 0;
  });

  list.innerHTML = sortedJobs
    .map((job) => {
      const cleanLocation = job.location && !job.location.toLowerCase().includes("berlin") ? job.location : "";
      const metaParts = [];
      if (cleanLocation) {
        metaParts.push(cleanLocation);
      }
      const dateText = job.postedDate ? formatJobDate(job.postedDate) : "-";
      const remoteText = job.remote && job.remote !== "No" ? job.remote : "On-site";
      const metaLocationText = metaParts.length ? `${remoteText} (${metaParts.join(", ")})` : remoteText;

      return `
        <div class="job-row">
          <span class="job-rank">#${job.originalRank}</span>
          <h3 class="job-title" title="${escapeHtml(job.title || '')}">${escapeHtml(job.title || "Untitled role")}</h3>
          <span class="job-company" title="${escapeHtml(job.company || '')}">${escapeHtml(job.company || "Unknown company")}</span>
          <span class="job-meta-inline">${escapeHtml(metaLocationText)}</span>
          <span class="job-meta-inline">${escapeHtml(dateText)}</span>
          <div class="job-row-right">
            ${job.link ? `
              <a class="job-external-link" href="${escapeHtml(job.link)}" target="_blank" rel="noreferrer" title="Open job details">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                  <polyline points="15 3 21 3 21 9"></polyline>
                  <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
              </a>
            ` : ""}
          </div>
        </div>
      `;
    })
    .join("");
}

function collectSettings() {
  const current = state.settings || {};
  return {
    ...current,
    includeLinkedIn: true,
    profileFitOnly: true,
    skipUpload: $("#skipUploadInput").checked,
    location: "Berlin, Germany",
    limitPerQuery: 25,
    postedWithinSeconds: 24 * 3600,
    delay: current.delay ?? 1,
    keywords: current.keywords,
  };
}

async function saveSettings() {
  const settings = await api("/api/settings", {
    method: "POST",
    body: JSON.stringify(collectSettings()),
  });
  state.settings = settings;
  $("#runLog").textContent = "Saved.";
  await refreshSummary();
}

let statusInterval = null;

function resetRunButton() {
  state.running = false;
  const button = $("#runBtn");
  button.disabled = false;
  button.textContent = "Run Daily Update";
  button.classList.add("primary-action");
  button.classList.remove("secondary-action");
}

function startPollingStatus() {
  if (statusInterval) clearInterval(statusInterval);
  statusInterval = setInterval(async () => {
    try {
      const status = await api("/api/run/status");
      const logArea = $("#runLog");
      logArea.textContent = status.logs || "";
      logArea.scrollTop = logArea.scrollHeight; // Auto-scroll to bottom

      if (!status.running) {
        clearInterval(statusInterval);
        resetRunButton();
        if (status.returnCode !== null) {
          $("#runLog").textContent += `\nFinished with code ${status.returnCode}`;
        }
        await refreshSummary();
        await loadJobs();
      }
    } catch (e) {
      console.error("Error polling status", e);
    }
  }, 1200);
}

async function runDailyUpdate() {
  const button = $("#runBtn");
  if (state.running) {
    button.disabled = true;
    button.textContent = "Stopping…";
    try {
      await api("/api/run/stop", { method: "POST" });
    } catch (e) {
      console.error(e);
      resetRunButton();
    }
    return;
  }

  // Start the background process
  button.textContent = "Stop Update";
  button.classList.add("secondary-action");
  button.classList.remove("primary-action");
  state.running = true;

  $("#runLog").textContent = "Starting daily update…\n";
  try {
    await saveSettings();
    await api("/api/run", { method: "POST", body: "{}" });
    startPollingStatus();
  } catch (error) {
    $("#runLog").textContent = `Update failed: ${error.message}`;
    resetRunButton();
  }
}

async function runSyncSheets() {
  const button = $("#syncBtn");
  button.disabled = true;
  $("#runLog").textContent = "Syncing Google Sheets…";
  try {
    const result = await api("/api/sync-sheets", { method: "POST", body: "{}" });
    const output = [result.stdout, result.stderr].filter(Boolean).join("\n");
    $("#runLog").textContent = output || `Finished with code ${result.returnCode}`;
    await refreshSummary();
    await loadJobs();
  } catch (error) {
    $("#runLog").textContent = `Sync failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function refreshSummary() {
  const summary = await api("/api/summary");
  renderSummary(summary);
}

function openSettings() {
  $("#settingsBackdrop").hidden = false;
  $("#settingsPanel").hidden = false;
}

function closeSettings() {
  $("#settingsBackdrop").hidden = true;
  $("#settingsPanel").hidden = true;
}

function bindEvents() {
  const debouncedLoad = debounce(loadJobs);
  ["#searchInput", "#roleSelect", "#remoteSelect"].forEach((selector) => {
    $(selector).addEventListener("input", debouncedLoad);
    $(selector).addEventListener("change", loadJobs);
  });

  $$(".source-tab").forEach((button) => {
    button.addEventListener("click", async () => {
      state.source = button.dataset.source;
      $$(".source-tab").forEach((item) => item.classList.toggle("active", item === button));
      await refreshSummary();
      await loadJobs();
    });
  });

  $("#settingsToggle").addEventListener("click", openSettings);
  $("#settingsClose").addEventListener("click", closeSettings);
  $("#settingsBackdrop").addEventListener("click", closeSettings);
  $("#saveSettingsBtn").addEventListener("click", saveSettings);
  $("#syncBtn").addEventListener("click", runSyncSheets);
  $("#runBtn").addEventListener("click", runDailyUpdate);

  // Bind sorting clicks to table headers
  const sortHeaders = {
    ".col-rank": "rank",
    ".col-title": "title",
    ".col-company": "company",
    ".col-mode": "mode",
    ".col-date": "date"
  };
  Object.entries(sortHeaders).forEach(([selector, field]) => {
    const el = $(selector);
    if (el) {
      el.addEventListener("click", () => {
        console.log("Header clicked! Field:", field, "Current state:", state.sortBy, state.sortAsc);
        if (state.sortBy === field) {
          state.sortAsc = !state.sortAsc;
        } else {
          state.sortBy = field;
          state.sortAsc = (field !== "rank" && field !== "date");
        }
        renderJobs(state.jobs);
      });
    }
  });
}

async function init() {
  bindEvents();
  await refreshSummary();
  await loadJobs();
  
  // Check if update is currently running in background
  try {
    const status = await api("/api/run/status");
    if (status.running) {
      state.running = true;
      const button = $("#runBtn");
      button.textContent = "Stop Update";
      button.classList.add("secondary-action");
      button.classList.remove("primary-action");
      startPollingStatus();
    }
  } catch (e) {
    console.error("Error fetching initial run status", e);
  }
}

init().catch((error) => {
  $("#jobsList").innerHTML = `<div class="empty-state">Could not load app data: ${escapeHtml(error.message)}</div>`;
});
