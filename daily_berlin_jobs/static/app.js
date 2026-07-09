const state = {
  source: "related",
  settings: null,
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
  $("#includeLinkedInInput").checked = Boolean(settings.includeLinkedIn);
  $("#profileFitOnlyInput").checked = Boolean(settings.profileFitOnly);
  $("#skipUploadInput").checked = Boolean(settings.skipUpload);
  $("#limitInput").value = settings.limitPerQuery ?? 25;
  $("#hoursInput").value = Math.round((settings.postedWithinSeconds ?? 86400) / 3600);
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
  renderJobs(payload.jobs || []);
}

function renderJobs(jobs) {
  const list = $("#jobsList");
  if (!jobs.length) {
    list.innerHTML = `<div class="empty-state">No roles match these filters yet.</div>`;
    return;
  }

  list.innerHTML = jobs
    .map((job) => {
      const meta = [job.location, job.remote && job.remote !== "No" ? job.remote : "", job.postedDate, job.ats]
        .filter(Boolean)
        .slice(0, 4);
      const note = job.fitReasons || job.department || compactText(job.description, 150);
      return `
        <article class="job-card">
          <div>
            <h3 class="job-title">${escapeHtml(job.title || "Untitled role")}</h3>
            <div class="job-company">${escapeHtml(job.company || "Unknown company")}</div>
          </div>
          <div class="job-meta">
            ${meta.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
          </div>
          <p class="job-note">${escapeHtml(note || "Software role")}</p>
          ${job.link ? `<a class="job-link" href="${escapeHtml(job.link)}" target="_blank" rel="noreferrer">Open role</a>` : ""}
        </article>
      `;
    })
    .join("");
}

function collectSettings() {
  const current = state.settings || {};
  return {
    ...current,
    includeLinkedIn: $("#includeLinkedInInput").checked,
    profileFitOnly: $("#profileFitOnlyInput").checked,
    skipUpload: $("#skipUploadInput").checked,
    location: "Berlin, Germany",
    limitPerQuery: Number($("#limitInput").value || 25),
    postedWithinSeconds: Number($("#hoursInput").value || 24) * 3600,
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

async function runDailyUpdate() {
  const button = $("#runBtn");
  button.disabled = true;
  $("#runLog").textContent = "Running daily update…";
  try {
    await saveSettings();
    const result = await api("/api/run", { method: "POST", body: "{}" });
    const output = [result.stdout, result.stderr].filter(Boolean).join("\n");
    $("#runLog").textContent = output || `Finished with code ${result.returnCode}`;
    await refreshSummary();
    await loadJobs();
  } catch (error) {
    $("#runLog").textContent = `Update failed: ${error.message}`;
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
  $("#runBtn").addEventListener("click", runDailyUpdate);
}

async function init() {
  bindEvents();
  await refreshSummary();
  await loadJobs();
}

init().catch((error) => {
  $("#jobsList").innerHTML = `<div class="empty-state">Could not load app data: ${escapeHtml(error.message)}</div>`;
});
