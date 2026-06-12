const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

function renderEnvironment() {
  const localHosts = new Set(["localhost", "127.0.0.1", "::1"]);
  const cloud = !localHosts.has(window.location.hostname);
  document.getElementById("workspace-status").textContent =
    cloud ? "Secure owner cloud" : "Local read-only workspace";
  document.getElementById("sign-out").hidden = !cloud;
}

function signed(value, suffix = "%") {
  if (value === null || value === undefined) return "--";
  return `${value >= 0 ? "+" : ""}${Number(value).toFixed(2)}${suffix}`;
}

function changeClass(value) {
  return Number(value) >= 0 ? "positive" : "negative";
}

function renderDashboard(data) {
  document.getElementById("as-of").textContent = data.generated_at
    ? `As of ${new Date(data.generated_at).toLocaleString()}`
    : "No Atlas snapshot available";

  const paper = data.paper || {};
  document.getElementById("equity").textContent = paper.configured ? money.format(paper.equity) : "--";
  document.getElementById("return").textContent = paper.configured
    ? `${signed(paper.total_return_pct)} total return`
    : "Paper account unavailable";
  document.getElementById("cash").textContent = paper.configured ? money.format(paper.cash) : "--";
  document.getElementById("cash-share").textContent = paper.configured && paper.equity
    ? `${((paper.cash / paper.equity) * 100).toFixed(1)}% of equity`
    : "Available capital";

  const overview = data.overview || {};
  document.getElementById("coverage").textContent = `${overview.available || 0}/${overview.tracked || 0}`;
  document.getElementById("breadth").textContent = `${overview.advancing || 0} up, ${overview.declining || 0} down`;
  document.getElementById("research-count").textContent = String(data.research?.open || 0);
  document.getElementById("research-detail").textContent =
    `${data.research?.high_priority || 0} high priority`;

  renderMarketPills(data.market || []);
  renderBreadth(overview);
  renderPerformance(data.history || []);
  renderScores(data.score_leaders || []);
  renderMovers(data.movers || []);
  renderSectors(data.sectors || []);
  renderPositions(paper.positions || []);
  renderTasks(data.research?.tasks || []);
  renderAccess(data.access || {});
  renderWorkspace(data.workspace || null);
}

function renderWorkspace(workspace) {
  const identity = document.getElementById("workspace-identity");
  if (!workspace?.tenant || !workspace?.account) {
    identity.hidden = true;
    return;
  }
  identity.hidden = false;
  document.getElementById("workspace-name").textContent =
    workspace.tenant.name;
  document.getElementById("workspace-role").textContent =
    workspace.account.role;
  document.getElementById("workspace-email").textContent =
    workspace.account.email;
}

function renderAccess(access) {
  document.getElementById("access-mode").textContent =
    access.mode === "invite_only" ? "Invite only" : "Restricted";
  document.getElementById("registration-status").textContent =
    access.public_registration ? "Enabled" : "Disabled";
  document.getElementById("tenant-isolation").textContent =
    access.tenant_isolation || "--";
  document.getElementById("identity-binding").textContent =
    access.identity_binding || "--";
  document.getElementById("audit-status").textContent =
    access.audit_log || "--";
  document.getElementById("threat-model-status").textContent =
    access.threat_model || "--";
  document.getElementById("recovery-status").textContent =
    access.recovery || "--";
  document.getElementById("privacy-export-status").textContent =
    access.privacy_export || "--";
  document.getElementById("account-deletion-status").textContent =
    access.account_deletion || "--";
  document.getElementById("access-roles").innerHTML = (access.roles || [])
    .map(role => `<span class="role-chip">${role}</span>`)
    .join("");
  const completion = Math.max(0, Math.min(100, Number(access.phase_completion) || 40));
  document.getElementById("phase-progress-label").textContent =
    `${completion}% complete`;
  document.getElementById("phase-progress-bar").style.width = `${completion}%`;
}

function renderMarketPills(rows) {
  document.getElementById("market-pills").innerHTML = rows.map(item => `
    <span class="market-pill">
      ${item.ticker} ${money.format(item.price || 0)}
      <b class="${changeClass(item.percent_change)}">${signed(item.percent_change)}</b>
    </span>
  `).join("");
}

function renderBreadth(overview) {
  const up = overview.advancing || 0;
  const down = overview.declining || 0;
  const total = Math.max(up + down, 1);
  const degrees = (up / total) * 360;
  const donut = document.getElementById("breadth-donut");
  donut.style.background = `conic-gradient(var(--green) 0deg ${degrees}deg, var(--red) ${degrees}deg 360deg)`;
  document.getElementById("breadth-center").textContent = `${Math.round((up / total) * 100)}%`;
  document.getElementById("advancing").textContent = number.format(up);
  document.getElementById("declining").textContent = number.format(down);
}

function renderPerformance(history) {
  const svg = document.getElementById("performance-chart");
  const width = 720;
  const height = 260;
  const pad = { left: 42, right: 18, top: 18, bottom: 30 };
  const series = [
    { key: "atlas_return", className: "atlas" },
    { key: "spy_return", className: "spy" },
    { key: "qqq_return", className: "qqq" },
  ];
  const values = history.flatMap(row => series.map(item => Number(row[item.key] || 0)));
  let min = Math.min(...values, -1);
  let max = Math.max(...values, 1);
  if (max - min < 2) { min -= 1; max += 1; }
  const x = index => pad.left + (history.length <= 1 ? 0 : index / (history.length - 1)) * (width - pad.left - pad.right);
  const y = value => pad.top + ((max - value) / (max - min)) * (height - pad.top - pad.bottom);
  const lines = [];
  for (let i = 0; i <= 4; i += 1) {
    const value = max - ((max - min) * i / 4);
    const py = y(value);
    lines.push(`<line class="chart-grid" x1="${pad.left}" y1="${py}" x2="${width - pad.right}" y2="${py}"/>`);
    lines.push(`<text class="chart-axis" x="4" y="${py + 3}">${value.toFixed(1)}%</text>`);
  }
  if (!history.length) {
    svg.innerHTML = `${lines.join("")}<text class="chart-axis" x="280" y="130">No performance history</text>`;
    return;
  }
  series.forEach(item => {
    const points = history.map((row, index) => `${x(index)},${y(Number(row[item.key] || 0))}`).join(" ");
    lines.push(`<polyline class="chart-path ${item.className}" points="${points}"/>`);
  });
  const firstLabel = new Date(history[0].timestamp).toLocaleDateString();
  const lastLabel = new Date(history[history.length - 1].timestamp).toLocaleDateString();
  lines.push(`<text class="chart-axis" x="${pad.left}" y="${height - 7}">${firstLabel}</text>`);
  lines.push(`<text class="chart-axis" text-anchor="end" x="${width - pad.right}" y="${height - 7}">${lastLabel}</text>`);
  svg.innerHTML = lines.join("");
}

function renderScores(rows) {
  document.getElementById("score-leaders").innerHTML = rows.map((item, index) => `
    <div class="rank-row">
      <span class="rank-number">${index + 1}</span>
      <span><b class="row-title">${item.ticker}</b><small class="row-meta">${item.sector} · ${item.category}</small></span>
      <strong class="score">${Number(item.score).toFixed(1)}</strong>
    </div>
  `).join("") || `<div class="empty">No score data available.</div>`;
}

function renderMovers(rows) {
  document.getElementById("movers").innerHTML = rows.map(item => `
    <div class="mover-row">
      <span><b class="row-title">${item.ticker}</b><small class="row-meta">${item.sector}</small></span>
      <strong class="change ${changeClass(item.percent_change)}">${signed(item.percent_change)}</strong>
    </div>
  `).join("") || `<div class="empty">No mover data available.</div>`;
}

function renderSectors(rows) {
  const maximum = Math.max(...rows.map(item => Math.abs(item.average_change)), 1);
  document.getElementById("sectors").innerHTML = rows.slice(0, 10).map(item => `
    <div class="sector-row">
      <div class="sector-label">
        <span>${item.sector}</span>
        <b class="${changeClass(item.average_change)}">${signed(item.average_change)}</b>
      </div>
      <div class="bar-track"><div class="bar ${item.average_change >= 0 ? "up" : "down"}" style="width:${Math.max(5, (Math.abs(item.average_change) / maximum) * 100)}%"></div></div>
    </div>
  `).join("") || `<div class="empty">No sector data available.</div>`;
}

function renderPositions(rows) {
  document.getElementById("positions").innerHTML = rows.map(item => {
    const review = item.review || {};
    return `
      <div class="position-row">
        <span>
          <b class="row-title">${item.ticker} · ${Number(item.shares).toFixed(0)} shares</b>
          <small class="row-meta">Average ${money.format(item.average_cost)} · ${review.verdict || "unreviewed"} thesis</small>
        </span>
        <span>
          <b class="row-title">${money.format(item.market_value || 0)}</b>
          <small class="row-meta ${changeClass(item.unrealized_gain_loss)}">${money.format(item.unrealized_gain_loss || 0)}</small>
        </span>
      </div>`;
  }).join("") || `<div class="empty">No open simulated positions.</div>`;
}

function renderTasks(rows) {
  document.getElementById("tasks").innerHTML = rows.map(item => `
    <div class="task-row">
      <span class="role-chip">${item.role}</span>
      <span><b class="row-title">${item.subject}</b><small class="row-meta">${item.prompt}</small></span>
    </div>
  `).join("") || `<div class="empty">No open research assignments.</div>`;
}

async function loadDashboard() {
  const error = document.getElementById("error-banner");
  error.hidden = true;
  try {
    const response = await fetch("/api/dashboard", { cache: "no-store" });
    if (!response.ok) throw new Error(`Dashboard request failed (${response.status})`);
    renderDashboard(await response.json());
  } catch (cause) {
    error.textContent = cause.message;
    error.hidden = false;
  }
}

document.getElementById("refresh").addEventListener("click", loadDashboard);
renderEnvironment();
loadDashboard();
