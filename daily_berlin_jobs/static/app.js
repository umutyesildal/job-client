const state = {
  source: "all",
  settings: null,
  summary: null,
  jobs: [],
  sortBy: "date",
  sortAsc: false,
  running: false,
};

const sourceLabels = {
  all: "All Jobs",
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

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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
  if (!value) return "Unknown";
  const raw = String(value).trim();
  if (raw.includes("ago") || raw.includes("hour") || raw.includes("day") || raw.includes("week")) {
    return raw;
  }
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function parseSortableDate(value) {
  const raw = String(value || "").trim();
  if (!raw) return 0;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return 0;
  return date.getTime();
}

function fillSettings(settings) {
  if (!settings) return;
  state.settings = settings;
  $("#includeLinkedInInput").checked = true;
  $("#limitInput").value = 25;
  $("#hoursInput").value = 24;
}

function preferredSortForSource(source) {
  return { sortBy: "date", sortAsc: false };
}

function renderSummary(summary) {
  state.summary = summary;
  const sources = summary.sources || {};

  $("#allTabCount").textContent = sources.all?.count ?? 0;
  $("#dailyTabCount").textContent = sources.daily?.count ?? 0;

  const activeSource = sources[state.source] || {};
  const updatedAt = activeSource.updatedAt || summary.lastRun?.finishedAt;
  $("#updatedText").textContent =
    `${sourceLabels[state.source]} \u00b7 ${activeSource.count ?? 0} roles \u00b7 Updated ${formatDate(updatedAt)}`;

  fillSettings(summary.settings);
}

function queryParams() {
  const params = new URLSearchParams();
  params.set("source", state.source);
  params.set("q", $("#searchInput").value.trim());
  params.set("level", $("#levelSelect").value);
  params.set("role", $("#roleSelect").value);
  params.set("remote", $("#remoteSelect").value);
  return params;
}

async function loadJobs() {
  const payload = await api(`/api/jobs?${queryParams().toString()}`);
  state.jobs = payload.jobs || [];
  renderJobs(state.jobs);
}

function updateHeaderSortIndicators() {
  const headers = {
    title: ".col-title",
    company: ".col-company",
    date: ".col-date",
  };

  Object.entries(headers).forEach(([key, selector]) => {
    const el = $(selector);
    if (!el) return;
    el.dataset.label = el.dataset.label || el.textContent.replace(/ [↑↓]$/, "");
    const base = el.dataset.label;
    if (state.sortBy === key) {
      el.textContent = `${base} ${state.sortAsc ? "↑" : "↓"}`;
      el.classList.add("active-sort");
    } else {
      el.textContent = base;
      el.classList.remove("active-sort");
    }
  });
}

function buildMetaPills(job) {
  const pills = [];
  const remoteText = String(job.remote || "").trim();
  if (remoteText && remoteText.toLowerCase() !== "no" && remoteText.toLowerCase() !== "on-site") {
    pills.push(remoteText);
  }

  return pills
    .filter(Boolean)
    .slice(0, 2)
    .map((pill) => `<span class="meta-pill">${escapeHtml(pill)}</span>`)
    .join("");
}

function sortJobs(jobs) {
  const sortedJobs = [...jobs];
  sortedJobs.sort((a, b) => {
    if (state.sortBy === "title") {
      const valA = (a.title || "").toLowerCase();
      const valB = (b.title || "").toLowerCase();
      if (valA < valB) return state.sortAsc ? -1 : 1;
      if (valA > valB) return state.sortAsc ? 1 : -1;
      return 0;
    }

    if (state.sortBy === "company") {
      const valA = (a.company || "").toLowerCase();
      const valB = (b.company || "").toLowerCase();
      if (valA < valB) return state.sortAsc ? -1 : 1;
      if (valA > valB) return state.sortAsc ? 1 : -1;
      return 0;
    }

    const dateA = parseSortableDate(a.postedDate);
    const dateB = parseSortableDate(b.postedDate);
    return state.sortAsc ? dateA - dateB : dateB - dateA;
  });
  return sortedJobs;
}

function renderJobs(jobs) {
  const list = $("#jobsList");
  if (!jobs.length) {
    list.innerHTML = `<div class="empty-state">No Berlin roles match this search right now.</div>`;
    return;
  }

  updateHeaderSortIndicators();

  list.innerHTML = sortJobs(jobs).map((job) => {
    const locationText = job.location || "Berlin";
    const metaPills = buildMetaPills(job);
    const rowTag = job.link ? "a" : "article";
    const rowAttrs = job.link
      ? `class="job-row job-row-link" href="${escapeHtml(job.link)}" target="_blank" rel="noreferrer"`
      : `class="job-row"`;

    return `
      <${rowTag} ${rowAttrs}>
        <div class="job-cell job-main">
          <h3 class="job-title" title="${escapeHtml(job.title || "")}">${escapeHtml(job.title || "Untitled role")}</h3>
        </div>
        <div class="job-cell job-company-cell">
          <span class="job-company" title="${escapeHtml(job.company || "")}">${escapeHtml(job.company || "Unknown company")}</span>
          <span class="job-location">${escapeHtml(locationText)}</span>
        </div>
        <div class="job-cell job-meta-cell">
          <div class="job-signals">
            ${metaPills || `<span class="job-meta-empty">-</span>`}
          </div>
        </div>
        <div class="job-cell job-date-cell">
          <span class="job-date">${escapeHtml(formatJobDate(job.postedDate))}</span>
        </div>
      </${rowTag}>
    `;
  }).join("");
}

function collectSettings() {
  const current = state.settings || {};
  return {
    ...current,
    includeLinkedIn: true,
    profileFitOnly: false,
    skipUpload: false,
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

function renderRunProgress(status) {
  const progress = Math.max(0, Math.min(Number(status.progress) || 0, 100));
  const container = $("#runProgress");
  container.hidden = false;
  $("#runStep").textContent = status.stepLabel || "Working...";
  $("#runPercent").textContent = `${progress}%`;
  $("#progressFill").style.width = `${progress}%`;
  const track = container.querySelector(".progress-track");
  track.setAttribute("aria-valuenow", String(progress));
}

function startPollingStatus() {
  if (statusInterval) clearInterval(statusInterval);
  statusInterval = setInterval(async () => {
    try {
      const status = await api("/api/run/status");
      renderRunProgress(status);
      const logArea = $("#runLog");
      logArea.textContent = status.logs || "";
      logArea.scrollTop = logArea.scrollHeight;

      if (!status.running) {
        clearInterval(statusInterval);
        resetRunButton();
        if (status.returnCode !== null) {
          $("#runLog").textContent += `\nFinished with code ${status.returnCode}`;
        }
        if (status.returnCode === 0) {
          await Promise.all([refreshSummary(), loadJobs()]);
        } else {
          await refreshSummary();
        }
      }
    } catch (error) {
      console.error("Error polling status", error);
    }
  }, 1200);
}

async function runDailyUpdate() {
  const button = $("#runBtn");
  if (state.running) {
    button.disabled = true;
    button.textContent = "Stopping...";
    try {
      await api("/api/run/stop", { method: "POST" });
    } catch (error) {
      console.error(error);
      resetRunButton();
    }
    return;
  }

  button.textContent = "Stop Update";
  button.classList.add("secondary-action");
  button.classList.remove("primary-action");
  state.running = true;

  $("#runLog").textContent = "Starting daily update...\n";
  renderRunProgress({ progress: 0, stepLabel: "Starting daily update" });
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
  $("#runLog").textContent = "Syncing Google Sheets...";
  renderRunProgress({ progress: 25, stepLabel: "Syncing canonical data from Google Sheets" });
  try {
    const result = await api("/api/sync-sheets", { method: "POST", body: "{}" });
    const output = [result.stdout, result.stderr].filter(Boolean).join("\n");
    $("#runLog").textContent = output || `Finished with code ${result.returnCode}`;
    if (result.returnCode !== 0) throw new Error(output || `Sync exited with code ${result.returnCode}`);
    renderRunProgress({ progress: 100, stepLabel: "Sheets sync complete" });
    await Promise.all([refreshSummary(), loadJobs()]);
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

  $("#searchInput").addEventListener("input", debouncedLoad);
  $("#searchInput").addEventListener("change", loadJobs);
  ["#levelSelect", "#roleSelect", "#remoteSelect"].forEach((selector) => {
    $(selector).addEventListener("change", loadJobs);
  });

  $$(".source-tab").forEach((button) => {
    button.addEventListener("click", async () => {
      state.source = button.dataset.source;
      Object.assign(state, preferredSortForSource(state.source));
      $$(".source-tab").forEach((item) => item.classList.toggle("active", item === button));
      if (state.summary) {
        renderSummary(state.summary);
      }
      await loadJobs();
    });
  });

  $("#settingsToggle").addEventListener("click", openSettings);
  $("#settingsClose").addEventListener("click", closeSettings);
  $("#settingsBackdrop").addEventListener("click", closeSettings);
  $("#saveSettingsBtn").addEventListener("click", saveSettings);
  $("#syncBtn").addEventListener("click", runSyncSheets);
  $("#runBtn").addEventListener("click", runDailyUpdate);

  const sortHeaders = {
    ".col-title": "title",
    ".col-company": "company",
    ".col-date": "date",
  };

  Object.entries(sortHeaders).forEach(([selector, field]) => {
    const el = $(selector);
    if (!el) return;
    el.addEventListener("click", () => {
      if (state.sortBy === field) {
        state.sortAsc = !state.sortAsc;
      } else {
        state.sortBy = field;
        state.sortAsc = field === "title" || field === "company";
        if (field === "date") {
          state.sortAsc = false;
        }
      }
      renderJobs(state.jobs);
    });
  });
}

async function init() {
  bindEvents();
  await refreshSummary();
  await loadJobs();

  try {
    const status = await api("/api/run/status");
    if (status.running) {
      state.running = true;
      renderRunProgress(status);
      const button = $("#runBtn");
      button.textContent = "Stop Update";
      button.classList.add("secondary-action");
      button.classList.remove("primary-action");
      startPollingStatus();
    }
  } catch (error) {
    console.error("Error fetching initial run status", error);
  }
}

init().catch((error) => {
  $("#jobsList").innerHTML =
    `<div class="empty-state">Could not load app data: ${escapeHtml(error.message)}</div>`;
});
