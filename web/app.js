const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const DASHBOARD_SUMMARY_CACHE_KEY = "atlas_dashboard_summary_v1";
const DASHBOARD_FULL_CACHE_KEY = "atlas_dashboard_full_v1";
let ownerControls = null;
let pendingPaperFill = null;
let paperTradeHistory = { total_trades: 0, ticker_count: 0, tickers: [] };
let paperAccountabilityReport = { summary: {}, tickers: [] };
let paperPositions = [];
let recommendationWatchlist = [];
let universeExpanded = false;
let recommendationView = "actions";
let reportArchive = [];
let reportArchiveFilter = "all";
let reportArchiveExpanded = false;

const PAGE_METADATA = {
  about: {
    eyebrow: "Atlas identity",
    title: "About Atlas",
    description: "The purpose, current capabilities, operating boundaries, and long-term direction of Atlas Capital Research.",
  },
  overview: {
    eyebrow: "Daily decision view",
    title: "Today",
    description: "See what Atlas recommends now, how the simulated portfolio is performing, and what needs attention.",
  },
  recommendations: {
    eyebrow: "Investment ideas",
    title: "Ideas",
    description: "Review Atlas buy, sell, and trim recommendations for the simulated portfolio.",
  },
  research: {
    eyebrow: "Research briefings",
    title: "Reports",
    description: "Read the latest Atlas briefing or open supporting research when you need more detail.",
  },
  paper: {
    eyebrow: "Simulated account",
    title: "Portfolio",
    description: "See current simulated holdings, performance, recent activity, and positions that need attention.",
  },
  controls: {
    eyebrow: "Policy workspace",
    title: "Controls",
    description: "Set the boundaries Atlas must follow while managing recommendations and the simulated paper portfolio.",
  },
  access: {
    eyebrow: "Security workspace",
    title: "Access and security",
    description: "Review owner access, recovery, privacy, deployment, and production-readiness safeguards.",
  },
  roadmap: {
    eyebrow: "Development workspace",
    title: "Atlas roadmap",
    description: "See the completed foundations, current validation stage, next gates, and owner-controlled path toward secure accounts and future trading autonomy.",
  },
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function conciseText(value, maxLength = 180) {
  const text = String(value || "").trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 3)).trim()}...`;
}

function researchTaskAgeLabel(item) {
  const raw = item?.created_at;
  if (!raw) return "date unavailable";
  const created = new Date(raw);
  if (Number.isNaN(created.getTime())) return "date unavailable";
  const days = Math.max(0, Math.floor((Date.now() - created.getTime()) / 86400000));
  if (days === 0) return "today";
  if (days === 1) return "1 day ago";
  return `${days} days ago`;
}

function safeExternalUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

function renderEnvironment() {
  const localHosts = new Set(["localhost", "127.0.0.1", "::1"]);
  const cloud = !localHosts.has(window.location.hostname);
  document.getElementById("workspace-status").textContent =
    cloud ? "Secure owner cloud" : "Local read-only workspace";
  document.getElementById("sign-out").hidden = !cloud;
}

function initializeHelpPopovers() {
  document.querySelectorAll(".info-popover").forEach(popover => {
    const trigger = popover.querySelector("summary");
    let closeTimer = null;
    const clearCloseTimer = () => {
      if (closeTimer) {
        window.clearTimeout(closeTimer);
        closeTimer = null;
      }
    };
    const openPopover = () => {
      clearCloseTimer();
      document.querySelectorAll(".info-popover[open]").forEach(other => {
        if (other !== popover) other.open = false;
      });
      popover.open = true;
    };
    const scheduleClose = () => {
      clearCloseTimer();
      closeTimer = window.setTimeout(() => {
        popover.open = false;
      }, 120);
    };
    if (trigger) {
      trigger.addEventListener("click", event => {
        event.preventDefault();
        if (popover.open) {
          popover.open = false;
          clearCloseTimer();
          return;
        }
        openPopover();
      });
      trigger.addEventListener("mouseenter", openPopover);
      trigger.addEventListener("mouseleave", scheduleClose);
      trigger.addEventListener("focus", openPopover);
      trigger.addEventListener("blur", scheduleClose);
    }
    popover.addEventListener("mouseenter", clearCloseTimer);
    popover.addEventListener("mouseleave", scheduleClose);
    popover.addEventListener("focusout", event => {
      if (!popover.contains(event.relatedTarget)) {
        scheduleClose();
      }
    });
  });
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    document.querySelectorAll(".info-popover[open]").forEach(popover => {
      popover.open = false;
    });
  });
  document.addEventListener("pointerdown", event => {
    document.querySelectorAll(".info-popover[open]").forEach(popover => {
      if (!popover.contains(event.target)) popover.open = false;
    });
  });
}

function signed(value, suffix = "%") {
  if (value === null || value === undefined) return "--";
  return `${value >= 0 ? "+" : ""}${Number(value).toFixed(2)}${suffix}`;
}

function changeClass(value) {
  return Number(value) >= 0 ? "positive" : "negative";
}

function clampScore(value) {
  return Math.max(0, Math.min(100, Number(value) || 0));
}

function atlasScoreLabel(value) {
  const score = Number(value);
  if (score >= 85) return "High priority";
  if (score >= 75) return "Strong";
  if (score >= 65) return "Watch";
  return "Developing";
}

function atlasScoreTone(value) {
  const score = Number(value);
  if (score >= 85) return "high";
  if (score >= 75) return "strong";
  if (score >= 65) return "watch";
  return "developing";
}

function renderScoreDrivers(item) {
  const scores = item.scores || {};
  const drivers = [
    ["Growth", scores.growth],
    ["Quality", scores.quality],
    ["Moat", scores.moat],
    ["Momentum", scores.momentum],
    ["Risk", scores.risk],
  ];
  return `
    <div class="score-driver-grid">
      ${drivers.map(([label, value]) => `
        <div class="score-driver ${label === "Risk" ? "risk" : ""}">
          <span><b>${label}</b><small>${value === null || value === undefined ? "--" : Number(value).toFixed(0)}</small></span>
          <i><em style="width:${clampScore(value)}%"></em></i>
        </div>
      `).join("")}
    </div>
    <div class="score-explanation-copy">
      ${item.thesis ? `<p><b>Thesis:</b> ${escapeHtml(item.thesis)}</p>` : ""}
      ${item.key_driver ? `<p><b>Key driver:</b> ${escapeHtml(item.key_driver)}</p>` : ""}
      ${item.key_risk ? `<p><b>Key risk:</b> ${escapeHtml(item.key_risk)}</p>` : ""}
      <small>${escapeHtml(item.score_horizon || "Research priority; not a return forecast")}</small>
    </div>
  `;
}

function benchmarkLabel(ticker) {
  if (ticker === "SPY") return "SPY (S&P 500 ETF benchmark)";
  if (ticker === "QQQ") return "QQQ (Nasdaq-100 ETF benchmark)";
  return String(ticker || "");
}

function setDataFreshness(state, detail = "") {
  const node = document.getElementById("data-freshness");
  const normalized = ["live", "cached", "loading"].includes(state) ? state : "loading";
  node.className = `data-freshness ${normalized}`;
  if (normalized === "live") {
    node.textContent = detail ? `Live · ${detail}` : "Live";
  }
  if (normalized === "cached") {
    node.textContent = detail ? `Cached snapshot · ${detail}` : "Cached snapshot";
    return;
  }
  node.textContent = detail ? `Refreshing · ${detail}` : "Refreshing";
}

function readCachedDashboardSummary() {
  try {
    const raw = window.localStorage.getItem(DASHBOARD_SUMMARY_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

function readCachedDashboardFull() {
  try {
    const raw = window.localStorage.getItem(DASHBOARD_FULL_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

function writeCachedDashboardSummary(data) {
  try {
    if (!data || typeof data !== "object" || !data.generated_at) return;
    window.localStorage.setItem(
      DASHBOARD_SUMMARY_CACHE_KEY,
      JSON.stringify(data),
    );
  } catch {
    return;
  }
}

function sanitizeDashboardForCache(data) {
  if (!data || typeof data !== "object" || !data.generated_at) return null;
  const clone = JSON.parse(JSON.stringify(data));
  delete clone.owner_controls;
  return clone;
}

function writeCachedDashboardFull(data) {
  try {
    const sanitized = sanitizeDashboardForCache(data);
    if (!sanitized) return;
    window.localStorage.setItem(
      DASHBOARD_FULL_CACHE_KEY,
      JSON.stringify(sanitized),
    );
  } catch {
    return;
  }
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
  renderMarketDataQuality(overview);
  document.getElementById("research-count").textContent = String(data.research?.open || 0);
  document.getElementById("research-detail").textContent =
    `${data.research?.high_priority || 0} high priority`;

  renderOwnerBriefing(data);
  renderMarketPills(data.market || []);
  renderBreadth(overview);
  renderPerformance(data.history || []);
  renderScores(data.score_leaders || []);
  renderMovers(data.movers || []);
  renderSectors(data.sectors || []);
  renderCorporateActions(data.corporate_actions || []);
  renderResearchWorkspace(data);
  renderPaperWorkspaceSummary(paper);
  renderThesisOverview(paper.thesis_overview || {});
  renderPortfolioFocus(paper.portfolio_focus || {});
  renderPositionLadder(paper.position_ladder || []);
  renderValidationSummary(paper.validation_summary || {});
  renderRoadmap(data);
  renderPositions(paper.positions || []);
  renderPaperActivity(paper.activity || []);
  renderTradeHistory(paper.trade_history || { total_trades: 0, ticker_count: 0, tickers: [] });
  renderAccountabilityReport(paper.accountability_report || { summary: {}, tickers: [] });
  renderPaperOperatingMode(paper.operating_mode || {});
  renderPaperFeedbackSummary(paper.feedback_summary || {});
  renderCapitalRotationScoreboard(paper.capital_rotation_scoreboard || {});
  renderPaperFeedback(paper.feedback || []);
  renderEntryEvidenceGate(data.overview || {});
  renderRecommendationSummary(data.owner_controls?.paper_proposals || [], data.watchlist || []);
  renderRecommendations(data.owner_controls?.paper_proposals || [], data.watchlist || []);
  renderTasks(data.research?.tasks || []);
  renderOwnerControls(data.owner_controls || null);
  renderAccess(data.access || {});
  renderWorkspace(data.workspace || null);
}

function renderDashboardSummary(data) {
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
  renderMarketDataQuality(overview);
  document.getElementById("research-count").textContent = String(data.research?.open || 0);
  document.getElementById("research-detail").textContent =
    `${data.research?.high_priority || 0} high priority`;

  renderOwnerBriefing(data);
  renderMarketPills(data.market || []);
  renderBreadth(overview);
  renderPerformance(data.history || []);
  renderPaperWorkspaceSummary(paper);
  renderThesisOverview(paper.thesis_overview || {});
  renderPortfolioFocus(paper.portfolio_focus || {});
  renderPositionLadder(paper.position_ladder || []);
  renderValidationSummary(paper.validation_summary || {});
  renderRoadmap(data);
  renderEntryEvidenceGate(data.overview || {});
  renderPositions(paper.positions || []);
  renderPaperOperatingMode(paper.operating_mode || {});
  renderWorkspace(data.workspace || null);
}

function hydrateDashboardFromCache() {
  const cachedFull = readCachedDashboardFull();
  if (cachedFull) {
    renderDashboard(cachedFull);
    setDataFreshness("cached");
    return true;
  }
  const cached = readCachedDashboardSummary();
  if (!cached) return false;
  renderDashboardSummary(cached);
  setDataFreshness("cached");
  return true;
}

function recommendationStageLabel(item) {
  if (item.auto_manage_enabled) {
    return item.status === "approved" ? "Auto-execution queued" : "Atlas auto-review queue";
  }
  if (item.side === "sell") {
    return proposalActionLabel(item) === "trim" ? "Trim candidate" : "Exit candidate";
  }
  return item.status === "approved" ? "Ready to simulate" : "Buy candidate";
}

function recommendationStageClass(item) {
  if (item.side === "sell") return "exit";
  return item.status === "approved" ? "ready" : "buy";
}

function recommendationRank(item) {
  if (item.side === "buy" && item.status === "approved") return 0;
  if (item.side === "buy") return 1;
  if (item.side === "sell" && proposalActionLabel(item) === "trim") return 2;
  return 3;
}

function recommendationCalibrationAdjustment(item) {
  return Number(item?.paper_calibration?.adjustment || 0);
}

function recommendationJudgedCount(item) {
  return Number(item?.paper_calibration?.judged || 0);
}

function compareRecommendations(left, right) {
  const stageGap = recommendationRank(left) - recommendationRank(right);
  if (stageGap !== 0) return stageGap;

  const calibrationGap =
    recommendationCalibrationAdjustment(right) - recommendationCalibrationAdjustment(left);
  if (calibrationGap !== 0) return calibrationGap;

  const judgedGap = recommendationJudgedCount(right) - recommendationJudgedCount(left);
  if (judgedGap !== 0) return judgedGap;

  const tickerLeft = String(left?.ticker || "");
  const tickerRight = String(right?.ticker || "");
  return tickerLeft.localeCompare(tickerRight);
}

function renderRecommendationSummary(proposals, watchlist) {
  const rows = proposals || [];
  const autoManaged = rows.some(item => item.auto_manage_enabled);
  const formalSellTickers = new Set(
    rows.filter(item => item.side === "sell").map(item => String(item.ticker || ""))
  );
  const positionAlerts = paperPositions
    .filter(item => ["trim", "exit"].includes(String(item.thesis_status?.label || "").toLowerCase()))
    .filter(item => !formalSellTickers.has(String(item.ticker || "")))
    .sort((left, right) => {
      const priority = { exit: 0, trim: 1 };
      return (priority[left.thesis_status?.label] ?? 2) - (priority[right.thesis_status?.label] ?? 2);
    });
  const summary = {
    buyPending: rows.filter(item => item.side === "buy" && item.status === "pending").length,
    buyReady: rows.filter(item => item.side === "buy" && item.status === "approved").length,
    reduce: rows.filter(item => item.side === "sell").length + positionAlerts.length,
  };
  const highlights = [
    ...positionAlerts.map(item => ({ kind: "position", item })),
    ...rows.slice().sort(compareRecommendations).map(item => ({ kind: "proposal", item })),
  ]
    .slice(0, 3);

  document.getElementById("recommendation-summary").innerHTML = `
    <div class="recommendation-summary-grid simplified">
      <div class="recommendation-summary-card">
        <span class="summary-label">Buy ideas under review</span>
        <strong>${summary.buyPending}</strong>
        <small>${autoManaged ? "Atlas is reviewing these automatically" : "Waiting for your decision"}</small>
      </div>
      <div class="recommendation-summary-card ready">
        <span class="summary-label">Ready to add</span>
        <strong>${summary.buyReady}</strong>
        <small>${autoManaged ? "Queued for automatic paper entry" : "Approved for the simulated portfolio"}</small>
      </div>
      <div class="recommendation-summary-card exit">
        <span class="summary-label">Sell or trim</span>
        <strong>${summary.reduce}</strong>
        <small>Positions Atlas recommends reducing</small>
      </div>
    </div>
    <div class="recommendation-summary-focus">
      <span class="access-label">What needs attention now</span>
      <div class="recommendation-focus-list">
        ${highlights.length ? highlights.map(entry => entry.kind === "position" ? `
          <div class="recommendation-focus-row urgent">
            <span class="thesis-badge ${escapeHtml(entry.item.thesis_status?.label || "watch")}">${escapeHtml(entry.item.thesis_status?.label || "review")}</span>
            <div>
              <b class="row-title">${escapeHtml(entry.item.ticker || "Holding")} position warning</b>
              <small class="row-meta">${escapeHtml(entry.item.thesis_status?.summary || "This simulated holding needs review.")}</small>
            </div>
          </div>
        ` : `
          <div class="recommendation-focus-row">
            <span class="thesis-badge ${recommendationStageClass(entry.item)}">${escapeHtml(recommendationStageLabel(entry.item))}</span>
            <div>
              <b class="row-title">${escapeHtml(entry.item.ticker || "Proposal")}</b>
              <small class="row-meta">${escapeHtml(primaryRationaleText(entry.item))}</small>
              ${entry.item.paper_calibration?.judged ? `<small class="row-meta">Paper learning ${recommendationCalibrationAdjustment(entry.item) >= 0 ? "+" : ""}${recommendationCalibrationAdjustment(entry.item).toFixed(0)} from ${recommendationJudgedCount(entry.item)} judged outcome${recommendationJudgedCount(entry.item) === 1 ? "" : "s"}</small>` : ""}
            </div>
          </div>
        `).join("") : `<div class="empty">No active recommendations or position warnings right now.</div>`}
      </div>
    </div>
  `;
}

function renderEntryEvidenceGate(overview) {
  const quality = overview.daily_change_quality || {};
  const limited = quality.status === "limited";
  const status = limited ? "paused" : "clear";
  const badge = limited ? "Waiting for valid refresh" : "Evidence clear";
  const title = limited
    ? "New simulated buys are automatically paused"
    : "Paper entry screening is active";
  const detail = limited
    ? "Prices did not provide a trustworthy daily comparison. Atlas will wait before adding positions; sell protections still run."
    : "Market data passed today's checks. Atlas can consider new paper positions within your limits.";
  const html = `
    <div class="entry-evidence-icon" aria-hidden="true">${limited ? "!" : "✓"}</div>
    <div>
      <span class="entry-evidence-label">Paper entry evidence</span>
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(detail)}</p>
    </div>
    <span class="entry-evidence-badge ${status}">${escapeHtml(badge)}</span>
  `;
  ["paper-entry-evidence", "roadmap-entry-evidence"].forEach(id => {
    const node = document.getElementById(id);
    if (!node) return;
    node.className = `entry-evidence-gate ${id === "roadmap-entry-evidence" ? "roadmap-entry-evidence " : ""}${status}`;
    node.innerHTML = html;
  });
}

function renderOwnerBriefing(data) {
  const paper = data.paper || {};
  const prospectiveTracker =
    paper.validation_summary?.prospective_review_tracker || {};
  const latestPriorityEscalations = Array.isArray(
    prospectiveTracker.latest_priority_escalations
  )
    ? prospectiveTracker.latest_priority_escalations
    : [];
  const focus = paper.portfolio_focus || {};
  const counts = focus.counts || {};
  const highlights = focus.highlights || [];
  const proposals = data.owner_controls?.paper_proposals || [];
  const currentMode = paper.operating_mode?.current || {};
  const autoManaged = currentMode.id === "paper_auto_manage";
  const dailyQuality = data.overview?.daily_change_quality || {};
  const entriesPaused = dailyQuality.status === "limited";
  const exitCount = Number(counts.exit || 0) + Number(counts.trim || 0);
  const pendingBuys = proposals.filter(item => item.side === "buy" && item.status === "pending").length;
  const readyBuys = proposals.filter(item => item.side === "buy" && item.status === "approved").length;
  const firstAttention = highlights.find(item =>
    ["watch", "trim", "exit"].includes(String(item.label || "").toLowerCase())
  ) || null;

  let attentionTitle = "No urgent portfolio review";
  let attentionDetail = "Atlas has not flagged a simulated holding for trim or exit.";
  if (firstAttention) {
    attentionTitle = `${firstAttention.ticker || "Holding"}: ${firstAttention.label || "review"}`;
    attentionDetail = firstAttention.summary || "Open the paper portfolio for the latest position review.";
  }

  let nextTitle = "No owner action required";
  let nextDetail = "Atlas will continue collecting evidence in the paper portfolio.";
  if (!autoManaged && exitCount > 0) {
    nextTitle = `Review ${exitCount} reduce or exit signal${exitCount === 1 ? "" : "s"}`;
    nextDetail = "Open Recommendations before acting on any simulated position change.";
  } else if (!autoManaged && readyBuys > 0) {
    nextTitle = `Simulate ${readyBuys} approved purchase${readyBuys === 1 ? "" : "s"}`;
    nextDetail = "Approved ideas still require you to record the simulated fill.";
  } else if (!autoManaged && pendingBuys > 0) {
    nextTitle = `Review ${pendingBuys} purchase candidate${pendingBuys === 1 ? "" : "s"}`;
    nextDetail = "Open Recommendations to accept or reject each paper idea.";
  } else if (autoManaged) {
    nextTitle = "Monitor paper results";
    nextDetail = "Atlas is managing simulation decisions automatically; real-money trading remains disabled.";
  }
  if (entriesPaused) {
    nextTitle = "Wait for a valid market refresh";
    nextDetail = "Atlas has paused new simulated buys. Independent trim and exit protections remain active.";
  }

  const operatingTitle = currentMode.label || (autoManaged ? "Automatic paper management" : "Recommendation mode");
  const paperReturn = paper.configured ? signed(Number(paper.total_return_pct || 0)) : "--";
  const paperResultTitle = paper.configured
    ? `${paperReturn} simulated return`
    : "Paper account unavailable";
  const paperResultDetail = paper.configured
    ? `${money.format(Number(paper.equity || 0))} equity with ${money.format(Number(paper.cash || 0))} in simulated cash.`
    : "Atlas needs a valid paper ledger before performance can be evaluated.";
  const positions = Array.isArray(paper.positions) ? paper.positions : [];
  const excessReturns = paper.excess_return_pct || {};
  const benchmarkEntries = Object.entries(excessReturns)
    .filter(([, value]) => value !== null && value !== undefined);
  const strongestEdge = benchmarkEntries.length
    ? benchmarkEntries.sort((left, right) => Number(right[1]) - Number(left[1]))[0]
    : null;
  const benchmarkEdgeLabel = strongestEdge
    ? `${signed(Number(strongestEdge[1]))} vs ${benchmarkLabel(strongestEdge[0])}`
    : "Building comparison history";
  const decisionState = entriesPaused
    ? "Entries paused"
    : exitCount > 0
      ? "Risk action"
      : pendingBuys + readyBuys > 0
        ? "Buy review"
        : "Monitoring";
  const decisionTone = entriesPaused ? "paused" : exitCount > 0 ? "risk" : "clear";

  document.getElementById("owner-briefing-grid").innerHTML = `
    <section class="owner-decision-card ${decisionTone}">
      <div class="owner-decision-heading">
        <span class="command-label">Atlas recommends</span>
        <b>${escapeHtml(decisionState)}</b>
      </div>
      <h3>${escapeHtml(nextTitle)}</h3>
      <p>${escapeHtml(nextDetail)}</p>
      <a href="#recommendations">${exitCount + pendingBuys + readyBuys ? "Review the action queue" : "Open recommendations"}</a>
      <small class="owner-mode-line">${escapeHtml(operatingTitle)}. Real-money trading is disabled.</small>
    </section>
    <section class="owner-portfolio-card">
      <span class="command-label">Simulated portfolio</span>
      <div class="portfolio-glance-primary">
        <strong class="${changeClass(Number(paper.total_return_pct || 0))}">${escapeHtml(paperResultTitle)}</strong>
        <small>${escapeHtml(benchmarkEdgeLabel)}</small>
      </div>
      <dl>
        <div><dt>Equity</dt><dd>${paper.configured ? money.format(Number(paper.equity || 0)) : "--"}</dd></div>
        <div><dt>Cash</dt><dd>${paper.configured ? money.format(Number(paper.cash || 0)) : "--"}</dd></div>
        <div><dt>Open positions</dt><dd>${positions.length}</dd></div>
      </dl>
    </section>
    <section class="owner-attention-strip ${firstAttention ? "active" : ""}">
      <span class="command-label">${firstAttention ? "Watch now" : "Portfolio status"}</span>
      <strong>${escapeHtml(attentionTitle)}</strong>
      <small>${escapeHtml(attentionDetail)}</small>
    </section>
  `;

  renderOwnerReportStatus(Array.isArray(data.reports) ? data.reports : []);

  const signalDigest = document.getElementById("owner-signal-digest");
  signalDigest.hidden = !prospectiveTracker.available || !latestPriorityEscalations.length;
  signalDigest.innerHTML = signalDigest.hidden ? "" : `
    <div class="owner-signal-digest-heading">
      <div>
        <span>Priority escalation watch</span>
        <b>${latestPriorityEscalations.length} new elevated-priority change${latestPriorityEscalations.length === 1 ? "" : "s"}</b>
      </div>
      <a href="#paper">Open tracker</a>
    </div>
    <div class="owner-signal-digest-list">
      ${latestPriorityEscalations.map(item => `
        <div class="owner-signal-digest-item ${escapeHtml(item.review_priority || "monitor")}">
          <div>
            <b>${escapeHtml(item.ticker || "Holding")}</b>
            <span>${escapeHtml(item.review_priority_label || "Monitor closely")}</span>
          </div>
          <small>${escapeHtml(item.previous_review_priority_label || "Prior level")} → ${escapeHtml(item.review_priority_label || "Elevated")} · ${Number(item.review_priority_score || 0)}/100</small>
        </div>
      `).join("")}
    </div>
    <small class="owner-signal-disclosure">Only upward moves into Monitor closely or Review now appear here. Alerts are review-only and cannot place or force a simulated trade.</small>
  `;
}

function renderOwnerReportStatus(reports) {
  const status = document.getElementById("owner-report-status");
  const link = document.getElementById("owner-latest-report-link");
  const latestDaily = reports.find(report => report.type === "Morning brief");
  const latest = latestDaily || reports[0] || null;
  if (!latest) {
    status.hidden = false;
    status.className = "owner-report-status missing";
    status.innerHTML = `
      <div>
        <span>Research delivery</span>
        <strong>No executive report is available</strong>
        <small>Open Research after the next scheduled run to confirm reporting resumed.</small>
      </div>
      <b>Missing</b>
    `;
    link.href = "#research";
    link.removeAttribute("target");
    link.removeAttribute("rel");
    link.textContent = "Open report library";
    return;
  }

  const generated = new Date(latest.generated_at);
  const ageHours = Number.isNaN(generated.getTime())
    ? Number.POSITIVE_INFINITY
    : Math.max(0, (Date.now() - generated.getTime()) / 3600000);
  const current = Boolean(latestDaily) && ageHours <= 36;
  status.hidden = current;
  const generatedLabel = Number.isFinite(ageHours)
    ? generated.toLocaleString([], {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : "date unavailable";
  const coverage = latest.coverage
    ? ` · ${Number(latest.coverage)} securities`
    : "";
  status.className = `owner-report-status ${current ? "current" : "delayed"}`;
  status.innerHTML = `
    <div>
      <span>Research delivery</span>
      <strong>${current ? "Latest briefing is current" : "Daily briefing needs a freshness check"}</strong>
      <small>${escapeHtml(latest.title || "Executive report")} · ${escapeHtml(generatedLabel)}${coverage}</small>
    </div>
    <b>${current ? "Current" : "Review"}</b>
  `;
  link.href = latest.url || "#research";
  link.target = "_blank";
  link.rel = "noopener";
  link.textContent = "Open latest report";
}

function setActivePage(pageId) {
  const requested = pageId || "overview";
  const normalized = requested === "market" ? "overview" : requested;
  const target = PAGE_METADATA[normalized] ? normalized : "overview";
  document.querySelectorAll(".dashboard-page").forEach(page => {
    page.classList.toggle("active-page", page.dataset.page === target);
  });
  document.querySelectorAll(".nav-item").forEach(link => {
    link.classList.toggle("active", link.getAttribute("href") === `#${target}`);
  });
  const metadata = PAGE_METADATA[target];
  document.getElementById("page-eyebrow").textContent = metadata.eyebrow;
  document.getElementById("page-title").textContent = metadata.title;
  document.getElementById("page-description").textContent = metadata.description;
  document.title = `${metadata.title} | Atlas Capital Research`;
}

function jumpToPageTarget(pageId, targetId) {
  setActivePage(pageId);
  const pageHash = `#${pageId}`;
  if (window.location.hash !== pageHash) {
    history.replaceState(null, "", pageHash);
  }
  const target = document.getElementById(String(targetId || ""));
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "center" });
}

function jumpToControlsTarget(targetId) {
  const target = document.getElementById(String(targetId || ""));
  const disclosure = target?.matches(".control-disclosure")
    ? target
    : target?.closest(".control-disclosure");
  if (disclosure) disclosure.open = true;
  jumpToPageTarget("controls", targetId);
}

function jumpToAccessTarget(targetId) {
  const target = document.getElementById(String(targetId || ""));
  const disclosure = target?.matches(".access-disclosure")
    ? target
    : target?.closest(".access-disclosure");
  if (disclosure) disclosure.open = true;
  jumpToPageTarget("access", targetId);
}

function jumpToPaperTarget(targetId) {
  jumpToPageTarget("paper", targetId);
}

function jumpToPaperSection(targetId) {
  const target = document.getElementById(String(targetId || ""));
  const disclosure = target?.querySelector(".paper-disclosure");
  if (disclosure) disclosure.open = true;
  jumpToPaperTarget(targetId);
}

function jumpToResearchTarget(targetId) {
  const target = document.getElementById(String(targetId || ""));
  const disclosure = target?.querySelector(".research-disclosure");
  if (disclosure) disclosure.open = true;
  jumpToPageTarget("research", targetId);
}

function renderWorkspace(workspace) {
  const identity = document.getElementById("workspace-identity");
  const revision = workspace?.deployment?.revision || "";
  const service = workspace?.deployment?.service || "";
  const hasTenantIdentity = Boolean(workspace?.tenant && workspace?.account);
  const hasDeploymentIdentity = Boolean(revision || service);
  if (!hasTenantIdentity && !hasDeploymentIdentity) {
    identity.hidden = true;
    return;
  }
  identity.hidden = false;
  const name = document.getElementById("workspace-name");
  const role = document.getElementById("workspace-role");
  const email = document.getElementById("workspace-email");
  const revisionNode = document.getElementById("workspace-revision");
  if (hasTenantIdentity) {
    name.hidden = false;
    role.hidden = false;
    email.hidden = false;
    name.textContent = workspace.tenant.name;
    role.textContent = workspace.account.role;
    email.textContent = workspace.account.email;
  } else {
    name.hidden = true;
    role.hidden = true;
    email.hidden = true;
  }
  if (hasDeploymentIdentity) {
    revisionNode.hidden = false;
    revisionNode.textContent = `Rev ${revision || "unknown"}${service ? ` · ${service}` : ""}`;
  } else {
    revisionNode.hidden = true;
  }
}

function renderAccess(access) {
  document.getElementById("access-mode").textContent =
    access.mode === "owner_only" ? "Owner only" : "Restricted";
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
  document.getElementById("production-review-status").textContent =
    access.production_review || "--";
  document.getElementById("access-roles").innerHTML = (access.roles || [])
    .map(role => `<span class="role-chip">${escapeHtml(role)}</span>`)
    .join("");
  const completion = Math.max(0, Math.min(100, Number(access.phase_completion) || 40));
  document.getElementById("phase-progress-label").textContent =
    `${completion}% complete`;
  document.getElementById("phase-progress-detail").textContent =
    `${completion}% complete`;
  document.getElementById("phase-progress-bar").style.width = `${completion}%`;
  const validation = Array.isArray(access.owner_validation) && access.owner_validation.length
    ? access.owner_validation
    : [
        {
          label: "Cross-device owner login",
          status: "pending",
          detail: "Confirm Joe can sign in from a second trusted device.",
        },
        {
          label: "Non-owner account denial",
          status: "pending",
          detail: "Confirm a different Google account is denied access.",
        },
      ];
  const pending = validation.filter(item => item.status !== "validated");
  document.getElementById("access-workspace-summary").innerHTML = `
    <div class="access-posture-grid">
      <div class="access-posture-card">
        <span class="access-label">Current access</span>
        <strong>${access.mode === "owner_only" ? "Owner only" : "Restricted"}</strong>
        <small>Only the approved owner identity can enter the private workspace.</small>
      </div>
      <div class="access-posture-card">
        <span class="access-label">Google identity</span>
        <strong>Verified</strong>
        <small>${escapeHtml(access.identity_binding || "Google identity binding is active.")}</small>
      </div>
      <div class="access-posture-card">
        <span class="access-label">Public signup</span>
        <strong>${access.public_registration ? "Enabled" : "Disabled"}</strong>
        <small>No public account creation or invitations are active.</small>
      </div>
      <div class="access-posture-card attention">
        <span class="access-label">Owner checks remaining</span>
        <strong>${pending.length}</strong>
        <small>Manual sign-in boundary checks before final owner-cloud sign-off.</small>
      </div>
    </div>
    <div class="access-owner-brief">
      <section>
        <span class="access-label">Protected now</span>
        <div class="access-protection-list">
          <div><span class="status-indicator active"></span><p><b>Private owner workspace</b><small>${escapeHtml(access.tenant_isolation || "Single-owner isolation is active.")}</small></p></div>
          <div><span class="status-indicator active"></span><p><b>Decision audit retained</b><small>${escapeHtml(access.audit_log || "Research and paper decisions are retained.")}</small></p></div>
          <div><span class="status-indicator active"></span><p><b>Recovery tested</b><small>${escapeHtml(access.recovery || "Integrity-checked recovery is available.")}</small></p></div>
        </div>
      </section>
      <section>
        <span class="access-label">Before inviting anyone else</span>
        <div class="access-validation-list">
          ${validation.map(item => `
            <div class="access-validation-row">
              <span class="status-indicator ${item.status === "validated" ? "active" : "watch"}"></span>
              <p><b>${escapeHtml(item.label || "Owner validation")}</b><small>${escapeHtml(item.detail || "Manual validation remains.")}</small></p>
              <span class="tag ${item.status === "validated" ? "healthy-tag" : ""}">${escapeHtml(item.status || "pending")}</span>
            </div>
          `).join("") || `<div class="empty">No owner-assisted validation checks are currently listed.</div>`}
        </div>
      </section>
    </div>
    <div class="access-summary-actions">
      <button class="secondary-button" type="button" data-access-target="access-controls-panel">Inspect security controls</button>
      <button class="secondary-button" type="button" data-access-target="access-future-panel">Review future account readiness</button>
    </div>
    <p class="access-boundary-note"><b>Current boundary:</b> Atlas is ready for Joe's private owner use. Multi-user invitations and public registration remain disabled.</p>
  `;
}

function renderControlWorkspace({
  researchAutoManageEnabled,
  autoManageEnabled,
  reviews,
  proposals,
  portfolioQueue,
  healthyHoldings,
  strategyPolicy,
}) {
  const target = document.getElementById("control-workspace-summary");
  const values = strategyPolicy.values || {};
  const manualProposals = proposals.filter(
    item => item.status !== "executed" && !item.auto_manage_enabled
  );
  const ownerAttention = reviews.length + manualProposals.length;
  const buyThreshold = Number(values.strategy_minimum_buy_score ?? 88);
  const exitThreshold = Number(values.strategy_maximum_exit_score ?? 60);
  const targetSize = Number(values.strategy_target_position_pct ?? 5);
  const buySlots = Number(values.strategy_maximum_new_proposals ?? 3);
  const trimEscalation = Number(values.maximum_partial_trims_per_position ?? 2);
  const paperMode = autoManageEnabled ? "Automatic paper management" : "Recommendations only";
  const researchMode = researchAutoManageEnabled ? "Automatic research review" : "Owner research review";

  target.innerHTML = `
    <div class="control-summary-grid">
      <div class="control-summary-card">
        <span class="access-label">Operating mode</span>
        <strong>${escapeHtml(paperMode)}</strong>
        <small>${autoManageEnabled ? "Atlas may record simulated fills after its risk gate." : "Paper proposals wait for owner approval and simulation."}</small>
      </div>
      <div class="control-summary-card">
        <span class="access-label">Owner attention</span>
        <strong>${ownerAttention}</strong>
        <small>${ownerAttention ? "Research or paper decisions are available for review." : "No manual decisions are waiting."}</small>
      </div>
      <div class="control-summary-card">
        <span class="access-label">Portfolio watch</span>
        <strong>${portfolioQueue.length}</strong>
        <small>Simulated holdings or proposals Atlas wants monitored.</small>
      </div>
      <div class="control-summary-card boundary-safe">
        <span class="access-label">Real-money authority</span>
        <strong>Disabled</strong>
        <small>No brokerage connection and no real trade execution.</small>
      </div>
    </div>
    <div class="control-brief-grid">
      <section>
        <span class="access-label">What Atlas can do now</span>
        <div class="control-brief-row">
          <span class="status-indicator active"></span>
          <div><b>${escapeHtml(researchMode)}</b><small>${reviews.length} current review item${reviews.length === 1 ? "" : "s"}.</small></div>
        </div>
        <div class="control-brief-row">
          <span class="status-indicator ${autoManageEnabled ? "active" : "watch"}"></span>
          <div><b>${escapeHtml(paperMode)}</b><small>Simulation only; normal paper risk checks remain active.</small></div>
        </div>
        <div class="control-brief-row">
          <span class="status-indicator blocked"></span>
          <div><b>Real trading blocked</b><small>Owner approval here cannot create a real-money order.</small></div>
        </div>
      </section>
      <section>
        <span class="access-label">Current paper guardrails</span>
        <div class="guardrail-grid">
          <div><small>Buy score</small><b>${buyThreshold.toFixed(1)}+</b></div>
          <div><small>Exit score</small><b>${exitThreshold.toFixed(1)} or below</b></div>
          <div><small>Target size</small><b>${targetSize.toFixed(1)}%</b></div>
          <div><small>New buy slots</small><b>${buySlots.toFixed(0)}</b></div>
          <div><small>Trim escalation</small><b>${trimEscalation.toFixed(0)} trims</b></div>
        </div>
      </section>
    </div>
    <div class="control-summary-actions">
      <button class="secondary-button" type="button" data-controls-target="control-decisions-panel">Review decisions</button>
      <button class="secondary-button" type="button" data-controls-target="control-strategy-panel">Edit paper strategy</button>
      <button class="secondary-button" type="button" data-controls-target="control-portfolio-panel">Inspect paper monitoring</button>
    </div>
    <p class="control-boundary-note"><b>Important:</b> every portfolio action on this page remains hypothetical and is recorded only in the Atlas paper account.</p>
  `;
}

function renderOwnerControls(controls) {
  ownerControls = controls;
  const available = Boolean(controls?.enabled && controls?.csrf_token);
  document.getElementById("control-content").hidden = !available;
  document.getElementById("control-availability").hidden = available;
  document.getElementById("control-boundary").textContent =
    controls?.boundary || "Owner cloud only";
  if (!available) return;

  const reviews = controls.research_reviews || [];
  const proposals = controls.paper_proposals || [];
  const autoManageEnabled = Boolean(controls.paper_auto_manage_enabled);
  const researchAutoManageEnabled = Boolean(
    controls.research_auto_manage_enabled ?? controls.paper_auto_manage_enabled
  );
  const controlsSummary = controls.controls_summary || {};
  const portfolioQueue = controls.portfolio_action_queue || [];
  const healthyHoldings = controls.healthy_holdings_summary || {};
  const strategyPolicy = controls.paper_strategy_policy || {};
  const adaptiveProfiles = strategyPolicy.adaptive_profiles || [];
  const buyCount = proposals.filter(item => item.side === "buy").length;
  const sellCount = proposals.filter(item => item.side === "sell").length;
  const actions = controls.daily_action_list || [];
  const outcomes = controls.owner_outcomes || {};
  document.getElementById("research-review-count").textContent =
    researchAutoManageEnabled
      ? `${reviews.length} manual review item${reviews.length === 1 ? "" : "s"}`
      : `${reviews.length} awaiting review`;
  document.getElementById("controls-summary-label").textContent =
    `${Number(controlsSummary.counts?.open_positions || 0).toFixed(0)} open holding${Number(controlsSummary.counts?.open_positions || 0) === 1 ? "" : "s"}`;
  document.getElementById("portfolio-action-count").textContent =
    `${portfolioQueue.length} watch item${portfolioQueue.length === 1 ? "" : "s"}`;
  document.getElementById("portfolio-watch-count").textContent =
    `${portfolioQueue.length} ranked item${portfolioQueue.length === 1 ? "" : "s"}`;
  document.getElementById("healthy-holdings-count").textContent =
    `${Number(healthyHoldings.count || 0).toFixed(0)} hold-steady holding${Number(healthyHoldings.count || 0) === 1 ? "" : "s"}`;
  document.getElementById("paper-proposal-count").textContent =
    `${buyCount} buy / ${sellCount} exit-trim`;
  renderRecommendations(proposals, null);
  renderOwnerOutcomes(outcomes);
  renderStrategyControls(strategyPolicy);
  renderControlWorkspace({
    researchAutoManageEnabled,
    autoManageEnabled,
    reviews,
    proposals,
    portfolioQueue,
    healthyHoldings,
    strategyPolicy,
  });
  document.getElementById("controls-summary").innerHTML = `
    <article class="decision-row">
      <div>
        <span class="tag">Controls summary</span>
        <b class="row-title">${escapeHtml(controlsSummary.headline || "Atlas is preparing the current paper-book posture summary.")}</b>
        <p>${escapeHtml(controlsSummary.posture || "Paper workflow posture is not available yet.")}</p>
        ${adaptiveProfiles.map(item => `<small class="row-meta">${escapeHtml(item.label)}: ${escapeHtml(String(item.value || "--"))} · ${escapeHtml(item.status || "watching")} · ${escapeHtml(item.detail || "")}</small>`).join("")}
        ${controlsSummary.freshest_change?.detail ? `<small class="row-meta">Freshest shift: ${escapeHtml(controlsSummary.freshest_change.detail)} ${escapeHtml(controlsSummary.freshest_change.timestamp_label || "recently")} in ${escapeHtml(controlsSummary.freshest_change.bucket_label || "the paper book")}.${controlsSummary.freshest_change.anchor_id ? ` <button type="button" class="inline-jump" data-controls-target="${escapeHtml(controlsSummary.freshest_change.anchor_id)}">Open item</button>` : ""}</small>` : ""}
        <small class="row-meta">Ranked queue: ${Number(controlsSummary.counts?.queue || 0).toFixed(0)} Â· Hold steady: ${Number(controlsSummary.counts?.healthy || 0).toFixed(0)} Â· Research reviews: ${Number(controlsSummary.counts?.research_reviews || 0).toFixed(0)}</small>
        <small class="row-meta">Paper proposals: ${Number(controlsSummary.counts?.buy_proposals || 0).toFixed(0)} buy Â· ${Number(controlsSummary.counts?.sell_proposals || 0).toFixed(0)} exit-trim</small>
      </div>
    </article>
  `;
  document.getElementById("portfolio-action-list").innerHTML = portfolioQueue.map(item => `
    <article class="decision-row" id="${escapeHtml(item.anchor_id || "")}">
      <div>
        <small class="row-meta">${escapeHtml(item.kind_label || "Portfolio item")}</small>
        ${item.is_freshest_shift ? `<span class="tag freshest-tag">${escapeHtml(item.freshness_label || "Freshest shift")}</span>` : ""}
        <span class="tag">${escapeHtml(item.status_label || "Review")} ${Number(item.attention_score || 0).toFixed(0)}</span>
        ${renderDecisionDriver(item.decision_driver)}
        <b class="row-title">${escapeHtml(item.title || item.subject || "Portfolio action")}</b>
        <p>${escapeHtml(item.summary || "Atlas wants attention on this portfolio item.")}</p>
        ${item.evidence_anchor ? `<small class="row-meta">Evidence anchor: ${escapeHtml(item.evidence_anchor)}</small>` : ""}
        ${item.portfolio_context ? `<small class="row-meta">Portfolio context: ${escapeHtml(item.portfolio_context)}</small>` : ""}
        ${item.paper_context ? `<small class="row-meta">Paper context: ${escapeHtml(item.paper_context)}</small>` : ""}
        ${renderNewsSummary(item.news_summary)}
        <small class="row-meta">Next step: ${escapeHtml(item.next_step || "Review this item in the paper workflow.")}</small>
      </div>
    </article>
  `).join("") || `<div class="empty">No paper proposals or open holdings currently need ranked portfolio attention.</div>`;
  document.getElementById("healthy-holdings-list").innerHTML = `
    <article class="decision-row">
      <div>
        <p>${escapeHtml(healthyHoldings.headline || "Atlas will show healthy holdings here when paper positions remain steady.")}</p>
      </div>
    </article>
    ${(healthyHoldings.items || []).map(item => `
      <article class="decision-row" id="${escapeHtml(item.anchor_id || "")}">
        <div>
          ${item.is_freshest_shift ? `<span class="tag freshest-tag">${escapeHtml(item.freshness_label || "Freshest shift")}</span>` : ""}
          <span class="tag healthy-tag">Hold steady</span>
          ${renderDecisionDriver(item.decision_driver)}
          <b class="row-title">${escapeHtml(item.ticker || "Holding")}</b>
          <p>${escapeHtml(item.summary || "Latest thesis review remains constructive.")}</p>
          ${Array.isArray(item.journal) && item.journal.length ? `<div class="why-now compact memory"><span>What changed since entry</span><ul>${item.journal.map(line => `<li>${escapeHtml(line)}</li>`).join("")}</ul></div>` : ""}
          ${item.portfolio_context ? `<small class="row-meta">Portfolio context: ${escapeHtml(item.portfolio_context)}</small>` : ""}
          ${item.paper_context ? `<small class="row-meta">Paper context: ${escapeHtml(item.paper_context)}</small>` : ""}
          ${renderDecisionDriver(item.decision_driver)}
          ${renderNewsSummary(item.news_summary)}
          <small class="row-meta ${changeClass(item.unrealized_gain_loss)}">Current paper result: ${money.format(Number(item.unrealized_gain_loss) || 0)}</small>
        </div>
      </article>
    `).join("")}
  `;
  document.getElementById("daily-action-list").innerHTML = actions.map(item => `
    <article class="decision-row">
      <div>
        ${(() => {
          const calibration = item.outcome_calibration || {};
          const reasons = calibration.reasons || [];
          return Number(calibration.adjustment || 0) || reasons.length
            ? `<small class="row-meta">Outcome calibration: ${Number(calibration.adjustment || 0) >= 0 ? "+" : ""}${Number(calibration.adjustment || 0).toFixed(0)}${reasons.length ? ` - ${reasons.map(reason => escapeHtml(reason)).join(", ")}` : ""}</small>`
            : "";
        })()}
        <span class="tag">${escapeHtml(item.attention_label || "Review")} ${Number(item.attention_score || 0).toFixed(0)}</span>
        <b class="row-title">${escapeHtml(item.subject || "Review")}</b>
        <p>${escapeHtml(item.summary || "Review this item.")}</p>
        ${item.evidence_anchor ? `<small class="row-meta">Evidence anchor: ${escapeHtml(item.evidence_anchor)}</small>` : ""}
        ${item.portfolio_context ? `<small class="row-meta">Portfolio context: ${escapeHtml(item.portfolio_context)}</small>` : ""}
        ${item.paper_context ? `<small class="row-meta">Paper context: ${escapeHtml(item.paper_context)}</small>` : ""}
        <small class="row-meta">Suggested disposition: ${escapeHtml(item.suggested_disposition || "Review")}</small>
      </div>
    </article>
  `).join("") || `<div class="empty">${researchAutoManageEnabled ? "Atlas auto-manages the current research review queue." : "No daily owner actions are awaiting review."}</div>`;
  document.getElementById("research-reviews").innerHTML = reviews.map(item => {
    const result = item.result || {};
    const evidence = (result.evidence || [])
      .filter(entry => typeof entry === "string" || entry.detail !== "Sector or broad-market context")
      .map(entry => {
      if (typeof entry === "string") {
        return `<li>${escapeHtml(entry)}</li>`;
      }
      const title = escapeHtml(entry.title || entry.detail || "Evidence");
      const source = escapeHtml(entry.source || "");
      const detail = escapeHtml(entry.detail || "");
      const url = safeExternalUrl(entry.url);
      const label = url
        ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${title}</a>`
        : title;
      return `<li>${label}${source ? ` <span class="evidence-source">${source}</span>` : ""}${detail ? `<small>${detail}</small>` : ""}</li>`;
      }).join("");
    return `
      <article class="decision-row">
        <div>
          <span class="role-chip">${escapeHtml(item.role)}</span>
          ${item.attention_label ? `<span class="tag">${escapeHtml(item.attention_label)} ${Number(item.attention_score || 0).toFixed(0)}</span>` : ""}
          <b class="row-title">${escapeHtml(item.subject)}</b>
          <small class="row-meta">${escapeHtml(result.recommendation || "Review")} · ${escapeHtml(result.confidence || "Unrated")}${result.catalyst_type ? ` · ${escapeHtml(result.catalyst_type).replaceAll("_", " ")}` : ""}</small>
          <p>${escapeHtml(result.conclusion || "No conclusion supplied.")}</p>
          ${(item.attention_reasons || []).length ? `<small class="row-meta">Attention drivers: ${item.attention_reasons.map(reason => escapeHtml(reason)).join(", ")}</small>` : ""}
          ${item.outcome_calibration?.adjustment ? `<small class="row-meta">Outcome calibration: ${Number(item.outcome_calibration.adjustment) >= 0 ? "+" : ""}${Number(item.outcome_calibration.adjustment).toFixed(0)}</small>` : ""}
          ${result.thesis_alignment ? `<small class="row-meta">Thesis alignment: ${escapeHtml(result.thesis_alignment).replaceAll("_", " ")}</small>` : ""}
          ${result.thesis_drift ? `<small class="row-meta">Thesis drift: ${escapeHtml(result.thesis_drift).replaceAll("_", " ")}</small>` : ""}
          ${result.thesis_action ? `<small class="row-meta">Thesis action: ${escapeHtml(result.thesis_action)}</small>` : ""}
          ${evidence ? `<details class="evidence-list"><summary>Review evidence</summary><ul>${evidence}</ul></details>` : ""}
        </div>
        <div class="decision-actions">
          ${researchAutoManageEnabled
            ? `<button type="button" class="secondary" disabled>Atlas auto-manages research reviews</button>`
            : `<button type="button" data-owner-action="research-decision" data-item-id="${escapeHtml(item.id)}" data-decision="approve">Approve</button>
          <button type="button" class="secondary" data-owner-action="research-decision" data-item-id="${escapeHtml(item.id)}" data-decision="defer">Defer</button>
          <button type="button" class="danger" data-owner-action="research-decision" data-item-id="${escapeHtml(item.id)}" data-decision="reject">Reject</button>`}
        </div>
      </article>`;
  }).join("") || `<div class="empty">${researchAutoManageEnabled ? "Atlas auto-resolved current research recommendations." : "No research recommendations await your decision."}</div>`;

  document.getElementById("paper-proposals").innerHTML = proposals.map(item => {
    const review = item.risk_review || {};
    const approved = item.status === "approved";
    const autoManaged = Boolean(item.auto_manage_enabled);
    return `
      <article class="decision-row">
        <div>
          <span class="tag ${item.side === "buy" ? "buy-tag" : "exit-tag"}">${escapeHtml(item.status)}</span>
          <b class="row-title">${proposalControlTitle(item)}</b>
          <small class="row-meta">Reference ${money.format(Number(item.reference_price) || 0)} · Risk ${escapeHtml(review.verdict || "pending")}</small>
          <p>${escapeHtml(item.thesis || "No thesis supplied.")}</p>
          ${proposalImpact(item)}
          ${renderNewsSummary(item.news_summary)}
          ${renderPaperCalibration(item.paper_calibration)}
          ${renderSellTrigger(item)}
          ${renderRationale(item.rationale, item)}
          ${renderObjections(item.objections, item)}
          <small class="row-meta">${autoManaged
            ? `Workflow: Atlas is in auto-manage mode, so it will review and record the hypothetical ${proposalActionLabel(item)} in Atlas paper tracking without waiting for owner approval.`
            : `Workflow: approve the paper idea first, then use Simulate fill to record the hypothetical ${proposalActionLabel(item)} in Atlas paper tracking.`}</small>
        </div>
        <div class="decision-actions">
          ${autoManaged ? `
            <button type="button" class="secondary" disabled>Atlas auto-manages this queue</button>
          ` : approved ? `
            <button type="button" class="simulate-button" data-owner-action="paper-fill" data-item-id="${escapeHtml(item.proposal_id)}">Simulate fill</button>
          ` : `
            <button type="button" data-owner-action="paper-decision" data-item-id="${escapeHtml(item.proposal_id)}" data-decision="approve">Approve</button>
            <button type="button" class="danger" data-owner-action="paper-decision" data-item-id="${escapeHtml(item.proposal_id)}" data-decision="reject">Reject</button>
          `}
        </div>
      </article>`;
  }).join("") || `<div class="empty">${autoManageEnabled ? "No paper proposals are waiting in the Atlas autonomous queue." : "No paper proposals require action."}</div>`;
}

function renderOwnerOutcomes(outcomes) {
  const counts = outcomes.research_decision_counts || {};
  const paper = outcomes.paper_proposal_counts || {};
  const approvalRate = outcomes.research_approval_rate_pct;
  const recent = (outcomes.recent_research_decisions || []).slice(0, 3)
    .map(item => `${escapeHtml(item.subject || "Review")}: ${escapeHtml(item.decision || "decision")}`)
    .join(" · ");
  document.getElementById("owner-outcomes").innerHTML = `
    <article class="decision-row">
      <div>
        <span class="tag">Outcome learning</span>
        <b class="row-title">${Number(outcomes.research_decisions || 0).toFixed(0)} research decisions recorded</b>
        <p>${escapeHtml(outcomes.learning_signal || "Atlas will summarize owner outcomes as decisions accumulate.")}</p>
        <small class="row-meta">Research: ${Number(counts.approve || 0)} approved · ${Number(counts.defer || 0)} deferred · ${Number(counts.reject || 0)} rejected${approvalRate === null || approvalRate === undefined ? "" : ` · ${Number(approvalRate).toFixed(1)}% approval rate`}</small>
        <small class="row-meta">Paper proposals: ${Number(paper.pending || 0)} pending · ${Number(paper.approved || 0)} approved · ${Number(paper.rejected || 0)} rejected · ${Number(paper.executed || 0)} simulated</small>
        ${recent ? `<small class="row-meta">Recent decisions: ${recent}</small>` : ""}
      </div>
    </article>
  `;
}

function renderStrategyControls(policy) {
  const target = document.getElementById("paper-strategy-controls");
  const values = policy.values || {};
  const adaptiveProfiles = policy.adaptive_profiles || [];
  if (!policy.available) {
    target.innerHTML = `<div class="empty">${escapeHtml(policy.headline || "Paper strategy controls are unavailable until the paper account is initialized.")}</div>`;
    return;
  }
  target.innerHTML = `
    <p>${escapeHtml(policy.headline || "Tune Atlas paper strategy from this page.")}</p>
    ${adaptiveProfiles.length ? `
      <div class="feedback-takeaways">
        ${adaptiveProfiles.map(item => `
          <div class="feedback-takeaway-card">
            <span class="access-label">${escapeHtml(item.label || "Adaptive profile")}</span>
            <strong>${escapeHtml(String(item.value || "--"))}</strong>
            <small>${escapeHtml(item.status || "watching")} · ${escapeHtml(item.detail || "")}</small>
          </div>
        `).join("")}
      </div>
    ` : ""}
    <form id="strategy-policy-form" class="strategy-policy-form">
      <div class="strategy-policy-grid">
        <label class="strategy-field toggle-field" for="policy-auto-manage-enabled">
          <span class="strategy-toggle">
            <input id="policy-auto-manage-enabled" name="auto_manage_enabled" type="checkbox" ${values.auto_manage_enabled ? "checked" : ""}>
            <span class="strategy-toggle-text">
              <b>Atlas autonomous paper mode</b>
              <small>When enabled, Atlas auto-approves and auto-executes paper trades after the normal risk-review gate.</small>
            </span>
          </span>
        </label>
        <label class="strategy-field" for="policy-buy-slots">
          <span>Buy slots</span>
          <input id="policy-buy-slots" name="strategy_maximum_new_proposals" type="number" min="1" max="10" step="1" value="${escapeHtml(values.strategy_maximum_new_proposals ?? 3)}">
          <small>How many new paper buy ideas Atlas can queue at once.</small>
        </label>
        <label class="strategy-field" for="policy-target-size">
          <span>Target size (%)</span>
          <input id="policy-target-size" name="strategy_target_position_pct" type="number" min="1" max="20" step="0.5" value="${escapeHtml(values.strategy_target_position_pct ?? 5)}">
          <small>Percent of starting simulated cash Atlas targets for each new entry.</small>
        </label>
        <label class="strategy-field" for="policy-buy-threshold">
          <span>Buy threshold</span>
          <input id="policy-buy-threshold" name="strategy_minimum_buy_score" type="number" min="50" max="100" step="0.5" value="${escapeHtml(values.strategy_minimum_buy_score ?? 88)}">
          <small>Minimum Atlas score required before a new buy proposal can open.</small>
        </label>
        <label class="strategy-field" for="policy-exit-threshold">
          <span>Exit threshold</span>
          <input id="policy-exit-threshold" name="strategy_maximum_exit_score" type="number" min="0" max="90" step="0.5" value="${escapeHtml(values.strategy_maximum_exit_score ?? 60)}">
          <small>Score level where Atlas becomes willing to exit or trim weaker holdings.</small>
        </label>
        <label class="strategy-field" for="policy-benchmark-weight">
          <span>Benchmark weight</span>
          <input id="policy-benchmark-weight" name="strategy_benchmark_excess_weight" type="number" min="0" max="5" step="0.1" value="${escapeHtml(values.strategy_benchmark_excess_weight ?? 1.5)}">
          <small>Extra emphasis on names outperforming SPY or QQQ.</small>
        </label>
        <label class="strategy-field" for="policy-trend-weight">
          <span>Trend weight</span>
          <input id="policy-trend-weight" name="strategy_trend_quality_weight" type="number" min="0" max="2" step="0.05" value="${escapeHtml(values.strategy_trend_quality_weight ?? 0.2)}">
          <small>Extra emphasis on higher-quality momentum leadership.</small>
        </label>
        <label class="strategy-field" for="policy-sector-diversity">
          <span>Sector diversity penalty</span>
          <input id="policy-sector-diversity" name="strategy_sector_repeat_penalty" type="number" min="0" max="10" step="0.5" value="${escapeHtml(values.strategy_sector_repeat_penalty ?? 3)}">
          <small>Penalty Atlas applies before doubling up inside one sector.</small>
        </label>
        <label class="strategy-field" for="policy-downside-filter">
          <span>Minimum daily move (%)</span>
          <input id="policy-downside-filter" name="strategy_minimum_daily_move_pct" type="number" min="-20" max="10" step="0.5" value="${escapeHtml(values.strategy_minimum_daily_move_pct ?? -8)}">
          <small>Prevents Atlas from buying names that are crashing beyond this daily-move limit.</small>
        </label>
      </div>
      <div class="strategy-actions">
        <div class="strategy-actions-group">
          <button type="button" class="secondary" data-strategy-preset="aggressive">Use aggressive preset</button>
          <button type="button" class="secondary" data-strategy-preset="balanced">Reset to current baseline</button>
        </div>
        <button id="strategy-policy-submit" type="submit">Save Atlas strategy</button>
      </div>
    </form>
  `;
}

function applyStrategyPreset(preset) {
  const presets = {
    aggressive: {
      auto_manage_enabled: true,
      strategy_maximum_new_proposals: 5,
      strategy_target_position_pct: 6.0,
      strategy_minimum_buy_score: 84.0,
      strategy_maximum_exit_score: 58.0,
      strategy_benchmark_excess_weight: 2.4,
      strategy_trend_quality_weight: 0.35,
      strategy_sector_repeat_penalty: 1.5,
      strategy_minimum_daily_move_pct: -6.0,
    },
    balanced: {
      auto_manage_enabled: true,
      strategy_maximum_new_proposals: 3,
      strategy_target_position_pct: 5.0,
      strategy_minimum_buy_score: 88.0,
      strategy_maximum_exit_score: 60.0,
      strategy_benchmark_excess_weight: 1.5,
      strategy_trend_quality_weight: 0.2,
      strategy_sector_repeat_penalty: 3.0,
      strategy_minimum_daily_move_pct: -8.0,
    },
  };
  const values = presets[preset];
  if (!values) return;
  Object.entries(values).forEach(([key, value]) => {
    const field = document.querySelector(`#strategy-policy-form [name="${key}"]`);
    if (!field) return;
    if (field.type === "checkbox") {
      field.checked = Boolean(value);
    } else {
      field.value = String(value);
    }
  });
}

function buildStrategyPolicyPayload(form) {
  return {
    auto_manage_enabled: Boolean(form.elements.auto_manage_enabled?.checked),
    strategy_maximum_new_proposals: Number(form.elements.strategy_maximum_new_proposals?.value),
    strategy_target_position_pct: Number(form.elements.strategy_target_position_pct?.value),
    strategy_minimum_buy_score: Number(form.elements.strategy_minimum_buy_score?.value),
    strategy_maximum_exit_score: Number(form.elements.strategy_maximum_exit_score?.value),
    strategy_benchmark_excess_weight: Number(form.elements.strategy_benchmark_excess_weight?.value),
    strategy_trend_quality_weight: Number(form.elements.strategy_trend_quality_weight?.value),
    strategy_sector_repeat_penalty: Number(form.elements.strategy_sector_repeat_penalty?.value),
    strategy_minimum_daily_move_pct: Number(form.elements.strategy_minimum_daily_move_pct?.value),
  };
}

async function submitStrategyPolicy(form) {
  const button = document.getElementById("strategy-policy-submit");
  await submitOwnerAction(
    "paper-policy",
    buildStrategyPolicyPayload(form),
    button
  );
}

function proposalActionLabel(item) {
  return item.action_label || (item.side === "sell" ? "exit or trim" : "purchase");
}

function proposalHeadline(item) {
  if (item.side === "sell") {
    return `${Number(item.shares).toFixed(2)} ${escapeHtml(item.ticker)} recommended for simulated ${escapeHtml(proposalActionLabel(item))}`;
  }
  return `${Number(item.shares).toFixed(2)} ${escapeHtml(item.ticker)} recommended for paper purchase`;
}

function proposalImpact(item) {
  if (item.side !== "sell") return "";
  const held = Number(item.position_shares || 0);
  const shares = Number(item.shares || 0);
  const remaining = Math.max(held - shares, 0);
  if (!held) {
    return `<small class="row-meta">Current simulated holding is unavailable, so Atlas is treating this as a sell review.</small>`;
  }
  if (proposalActionLabel(item) === "trim") {
    return `<small class="row-meta">Would reduce the simulated holding from ${held.toFixed(2)} shares to ${remaining.toFixed(2)} shares.</small>`;
  }
  if (proposalActionLabel(item) === "exit") {
    return `<small class="row-meta">Would close the full simulated holding of ${held.toFixed(2)} shares.</small>`;
  }
  return `<small class="row-meta">Current simulated holding: ${held.toFixed(2)} shares.</small>`;
}

function renderSellTrigger(item) {
  if (item.side !== "sell") return "";
  const summary = String(item.sell_trigger_summary || "").trim();
  const reasons = Array.isArray(item.sell_trigger_reasons) ? item.sell_trigger_reasons.filter(Boolean) : [];
  if (!summary && !reasons.length) return "";
  return `
    <div class="why-now compact memory">
      <span>${escapeHtml(proposalActionLabel(item) === "trim" ? "Trim trigger" : "Exit trigger")}</span>
      ${summary ? `<p>${escapeHtml(summary)}</p>` : ""}
      ${reasons.length ? `<ul>${reasons.map(reason => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>` : ""}
    </div>
  `;
}

function renderPaperCalibration(calibration) {
  const judged = Number(calibration?.judged || 0);
  const tickerJudged = Number(calibration?.ticker_judged || 0);
  const adjustment = Number(calibration?.adjustment || 0);
  const reasons = Array.isArray(calibration?.reasons) ? calibration.reasons : [];
  const label = String(calibration?.label || "neutral");
  if (!judged && !reasons.length && !adjustment) {
    return `<small class="row-meta">Paper learning: not enough judged simulated outcomes yet.</small>`;
  }
  const tone = label === "supportive" ? "supportive" : label === "caution" ? "caution" : "neutral";
  const reasonText = reasons.length ? ` - ${reasons.map(reason => escapeHtml(reason)).join(", ")}` : "";
  const tickerText = tickerJudged ? ` - ${tickerJudged} judged ticker-specific outcome${tickerJudged === 1 ? "" : "s"}` : "";
  return `<small class="row-meta paper-calibration ${tone}">Paper learning: ${adjustment >= 0 ? "+" : ""}${adjustment.toFixed(0)}${reasonText}${tickerText}</small>`;
}

function proposalControlTitle(item) {
  if (item.side === "sell") {
    return `${escapeHtml(proposalActionLabel(item).toUpperCase())} ${Number(item.shares).toFixed(2)} ${escapeHtml(item.ticker)}`;
  }
  return `${escapeHtml(item.side).toUpperCase()} ${Number(item.shares).toFixed(2)} ${escapeHtml(item.ticker)}`;
}

function renderRecommendationEvidence(item, tradePressureProfile, benchmarkTrustProfile) {
  return `
    <details class="evidence-disclosure">
      <summary>View evidence</summary>
      <div class="evidence-content">
        ${renderPaperCalibration(item.paper_calibration)}
        ${tradePressureProfile ? `<small class="row-meta">Adaptive trade pressure: ${escapeHtml(String(tradePressureProfile.value || "--"))} daily trades - ${escapeHtml(tradePressureProfile.status || "watching")}</small>` : ""}
        ${benchmarkTrustProfile ? `<small class="row-meta">Adaptive benchmark trust: ${escapeHtml(String(benchmarkTrustProfile.value || "AUTO"))} - ${escapeHtml(benchmarkTrustProfile.status || "watching")}</small>` : ""}
        ${item.side === "sell" ? renderSellTrigger(item) : ""}
        ${renderRationale(item.rationale, item)}
        ${renderObjections(item.objections, item)}
      </div>
    </details>`;
}

function renderRecommendations(proposals, watchlist) {
  const adaptiveProfiles = ownerControls?.paper_strategy_policy?.adaptive_profiles || [];
  const tradePressureProfile = adaptiveProfiles.find(item => item.id === "trade_pressure") || null;
  const benchmarkTrustProfile = adaptiveProfiles.find(item => item.id === "benchmark_trust") || null;
  const buyProposals = (proposals || [])
    .filter(item => item.side === "buy")
    .sort(compareRecommendations);
  const sellProposals = (proposals || [])
    .filter(item => item.side === "sell")
    .sort(compareRecommendations);
  const formalSellTickers = new Set(sellProposals.map(item => String(item.ticker || "")));
  const positionAlerts = paperPositions
    .filter(item => ["trim", "exit"].includes(String(item.thesis_status?.label || "").toLowerCase()))
    .filter(item => !formalSellTickers.has(String(item.ticker || "")))
    .sort((left, right) => {
      const priority = { exit: 0, trim: 1 };
      return (priority[left.thesis_status?.label] ?? 2) - (priority[right.thesis_status?.label] ?? 2);
    });
  const buyHtml = buyProposals.map(item => `
    <article class="recommendation-row ${item.status === "approved" ? "approved-rec" : ""}">
      <span class="tag ${item.status === "approved" ? "ready-tag" : "buy-tag"}">${escapeHtml(recommendationStageLabel(item))}</span>
      <div>
        <b class="row-title">${proposalHeadline(item)}</b>
        <small class="row-meta">Reference ${money.format(Number(item.reference_price) || 0)} - ${escapeHtml(item.thesis || "No thesis supplied.")}</small>
        <small class="row-meta">${item.auto_manage_enabled
          ? (item.status === "approved"
            ? "Status: Atlas already approved this idea in auto-manage mode and will record the paper fill automatically."
            : "Status: Atlas is holding this in its autonomous review queue instead of waiting for owner approval.")
          : (item.status === "approved"
            ? "Status: approved by owner and ready for Simulate fill."
            : "Status: Atlas recommends this idea, but it still needs owner approval.")}</small>
        ${renderRecommendationEvidence(item, tradePressureProfile, benchmarkTrustProfile)}
        <small class="row-meta">${item.auto_manage_enabled
          ? (item.status === "approved"
            ? "Next step: Atlas will record the paper fill automatically when the next autonomous cycle has a usable market price."
            : "Next step: Atlas will auto-review this paper proposal after the risk gate runs.")
          : (item.status === "approved"
            ? "Next step: use Simulate fill to add this to the paper portfolio."
            : "Next step: approve or reject this paper proposal in Controls.")}</small>
      </div>
    </article>
  `).join("") || `<div class="empty">No current paper purchase recommendations. Future Atlas-generated proposals will include a Why now rationale before any owner decision.</div>`;
  ["recommended-buys", "overview-recommended-buys"].forEach(id => {
    const target = document.getElementById(id);
    if (target) target.innerHTML = buyHtml;
  });
  const proposalSellHtml = sellProposals.map(item => `
    <article class="recommendation-row exit-rec ${item.status === "approved" ? "approved-rec" : ""}">
      <span class="tag exit-tag">${escapeHtml(recommendationStageLabel(item))}</span>
      <div>
        <b class="row-title">${proposalHeadline(item)}</b>
        <small class="row-meta">Reference ${money.format(Number(item.reference_price) || 0)} - ${escapeHtml(item.thesis || "No thesis supplied.")}</small>
        <small class="row-meta">${item.auto_manage_enabled
          ? `Status: Atlas wants to ${escapeHtml(proposalActionLabel(item))} simulated exposure in this holding and will handle the paper workflow automatically.`
          : `Status: Atlas wants to ${escapeHtml(proposalActionLabel(item))} simulated exposure in this holding.`}</small>
        ${proposalImpact(item)}
        ${renderRecommendationEvidence(item, tradePressureProfile, benchmarkTrustProfile)}
        <small class="row-meta">${item.auto_manage_enabled
          ? (item.status === "approved"
            ? `Next step: Atlas will record this simulated ${proposalActionLabel(item)} automatically on the next autonomous cycle.`
            : `Next step: Atlas will auto-review this simulated ${proposalActionLabel(item)} proposal after the risk gate runs.`)
          : (item.status === "approved"
            ? `Next step: use Simulate fill to record this simulated ${proposalActionLabel(item)}.`
            : `Next step: approve or reject this simulated ${proposalActionLabel(item)} proposal in Controls.`)}</small>
      </div>
    </article>
  `).join("");
  const positionAlertHtml = positionAlerts.map(item => {
    const thesis = item.thesis_status || {};
    return `
      <article class="recommendation-row exit-rec position-alert">
        <span class="thesis-badge ${escapeHtml(thesis.label || "watch")}">${escapeHtml(thesis.label || "review")}</span>
        <div>
          <b class="row-title">${escapeHtml(item.ticker || "Holding")} needs ${escapeHtml(thesis.label || "risk")} review</b>
          <small class="row-meta">${escapeHtml(thesis.summary || "This simulated holding has weakened and needs review.")}</small>
          <small class="row-meta ${changeClass(item.unrealized_gain_loss)}">Open simulated result: ${money.format(Number(item.unrealized_gain_loss) || 0)}</small>
          ${renderDecisionDriver(item.decision_driver)}
          <small class="row-meta">This is a position warning, not a completed simulated sale or a real-money order.</small>
          <div class="position-alert-actions">
            <button class="secondary-button" type="button" data-paper-target="${escapeHtml(item.anchor_id || "")}">Review holding</button>
          </div>
          <details class="evidence-disclosure">
            <summary>View evidence</summary>
            <div class="evidence-content">
              ${renderNewsSummary(item.news_summary)}
              ${item.research_memory?.summary ? `<small class="row-meta">Research memory: ${escapeHtml(item.research_memory.summary)}</small>` : ""}
              ${(item.decision_journal || []).length ? `<div class="why-now"><span>What changed</span><ul>${item.decision_journal.slice(0, 4).map(line => `<li>${escapeHtml(line)}</li>`).join("")}</ul></div>` : ""}
            </div>
          </details>
        </div>
      </article>`;
  }).join("");
  const sellHtml = proposalSellHtml + positionAlertHtml ||
    `<div class="empty">No current paper exit or trim recommendations. Atlas will surface one here if an open simulated position weakens.</div>`;
  ["recommended-exits", "overview-recommended-exits"].forEach(id => {
    const target = document.getElementById(id);
    if (target) target.innerHTML = sellHtml;
  });

  if (watchlist === null) return;
  const previewRows = (watchlist || []).slice(0, 12).map(item => `
    <div class="watchlist-item compact">
      <b>${escapeHtml(item.ticker)}</b>
      <span>${escapeHtml(item.category || "Tracked")}</span>
    </div>
  `).join("") || `<div class="empty">No tracked securities available.</div>`;
  const fullTarget = document.getElementById("current-watchlist");
  const previewTarget = document.getElementById("overview-current-list");
  recommendationWatchlist = Array.isArray(watchlist) ? watchlist : [];
  if (fullTarget) renderUniverseList();
  if (previewTarget) previewTarget.innerHTML = previewRows;
}

function renderUniverseList() {
  const target = document.getElementById("current-watchlist");
  if (!target) return;
  const search = String(document.getElementById("universe-search")?.value || "").trim().toLowerCase();
  const category = String(document.getElementById("universe-category")?.value || "all");
  const filtered = recommendationWatchlist
    .filter(item => category === "all" || item.category === category)
    .filter(item => {
      if (!search) return true;
      return [item.ticker, item.sector, item.category]
        .some(value => String(value || "").toLowerCase().includes(search));
    })
    .sort((left, right) => {
      const scoreGap = Number(right.score ?? -1) - Number(left.score ?? -1);
      return scoreGap || String(left.ticker || "").localeCompare(String(right.ticker || ""));
    });
  const visible = universeExpanded || search ? filtered : filtered.slice(0, 24);
  const cards = visible.map(item => `
    <article class="watchlist-item score-universe-item ${item.category === "Core" ? "core" : item.category === "Watchlist" ? "watchlist" : "tracked"}">
      <div class="score-universe-heading">
        <div>
          <b>${escapeHtml(item.ticker)}</b>
          <span>${escapeHtml(item.category || "Tracked")}</span>
        </div>
        ${item.score === null || item.score === undefined ? "" : `
          <strong class="atlas-score-badge ${atlasScoreTone(item.score)}">${Number(item.score).toFixed(0)}</strong>
        `}
      </div>
      <small>${escapeHtml(item.company_name || item.ticker)} &middot; ${escapeHtml(item.sector || "Unclassified")}</small>
      ${item.score === null || item.score === undefined ? "" : `
        <details class="score-explanation">
          <summary>${atlasScoreLabel(item.score)} &middot; Explain score</summary>
          ${renderScoreDrivers(item)}
        </details>
      `}
    </article>
  `);
  target.classList.toggle("score-universe-layout", cards.length > 0);
  target.innerHTML = cards.length
    ? Array.from({ length: Math.ceil(cards.length / 2) }, (_, index) => `
        <div class="score-universe-row">
          ${cards.slice(index * 2, (index * 2) + 2).join("")}
        </div>
      `).join("")
    : `<div class="empty">No tracked securities match these filters.</div>`;

  const count = document.getElementById("universe-result-count");
  if (count) {
    count.textContent = `Showing ${visible.length} of ${filtered.length} matching securities (${recommendationWatchlist.length} tracked)`;
  }
  const toggle = document.getElementById("universe-toggle");
  if (toggle) {
    toggle.hidden = Boolean(search) || filtered.length <= 24;
    toggle.textContent = universeExpanded ? "Show top scores" : "Show all";
  }
}

function renderRationale(rationale, item = {}) {
  const rows = effectiveRationaleRows(rationale, item);
  if (!rows.length && item.side === "buy") {
    rows.push(
      "This proposal was created before structured Why now rationale was stored. New Atlas-generated proposals will include score, category, sector, move, and sizing rationale."
    );
  } else if (!rows.length && item.side === "sell") {
    rows.push(
      "Atlas created this simulated exit review because the open paper position triggered thesis, score, or drawdown monitoring rules."
    );
  }
  if (!rows.length) return "";
  const sellHeading = proposalActionLabel(item) === "trim" ? "Why trim" : "Why exit";
  return `
    <div class="why-now">
      <span>${item.side === "sell" ? sellHeading : "Why now"}</span>
      <ul>${rows.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>`;
}

function renderObjections(objections, item = {}) {
  const rows = (objections || []).filter(Boolean);
  if (!rows.length) return "";
  const heading = item.side === "sell" ? "What could go wrong" : "Why not";
  return `
    <div class="why-not">
      <span>${heading}</span>
      <ul>${rows.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>`;
}

function effectiveRationaleRows(rationale, item = {}) {
  const rows = (rationale || []).filter(Boolean);
  if (rows.length) return rows;
  const thesis = String(item.thesis || "").trim();
  if (!thesis) return [];
  const fallback = [thesis];
  const calibrationSummary = String(item.paper_calibration?.summary || "").trim();
  if (calibrationSummary) fallback.push(calibrationSummary);
  return fallback;
}

function primaryRationaleText(item = {}) {
  return effectiveRationaleRows(item.rationale, item)[0] || "Awaiting rationale.";
}

function renderMarketPills(rows) {
  document.getElementById("market-pills").innerHTML = rows.map(item => `
    <span class="market-pill">
      ${item.ticker} ${money.format(item.price || 0)}
      <b class="${changeClass(item.percent_change)}">${signed(item.percent_change)}</b>
    </span>
  `).join("");
}

function renderMarketDataQuality(overview) {
  const quality = overview.daily_change_quality || {};
  const limited = quality.status === "limited";
  const warning = document.getElementById("market-data-warning");
  warning.hidden = !limited;
  document.getElementById("market-data-warning-detail").textContent =
    quality.detail || "Atlas is waiting for a valid prior-close comparison.";
  document.getElementById("breadth").textContent = limited
    ? "Daily movement unavailable"
    : `${overview.advancing || 0} up, ${overview.declining || 0} down`;
}

function renderBreadth(overview) {
  const up = overview.advancing || 0;
  const down = overview.declining || 0;
  const limited = overview.daily_change_quality?.status === "limited";
  const total = Math.max(up + down, 1);
  const degrees = (up / total) * 360;
  const donut = document.getElementById("breadth-donut");
  donut.style.background = limited
    ? "conic-gradient(var(--line-strong) 0deg 360deg)"
    : `conic-gradient(var(--green) 0deg ${degrees}deg, var(--red) ${degrees}deg 360deg)`;
  document.getElementById("breadth-center").textContent = limited
    ? "--"
    : `${Math.round((up / total) * 100)}%`;
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

function renderResearchWorkspace(data) {
  const leaders = Array.isArray(data.score_leaders) ? data.score_leaders : [];
  const movers = Array.isArray(data.movers) ? data.movers : [];
  const sectors = Array.isArray(data.sectors) ? data.sectors : [];
  const research = data.research || {};
  const tasks = Array.isArray(research.tasks) ? research.tasks : [];
  const leader = leaders[0] || null;
  const mover = movers[0] || null;
  const strongestSector = sectors[0] || null;
  const weakestSector = sectors.length ? sectors[sectors.length - 1] : null;
  renderReportArchive(Array.isArray(data.reports) ? data.reports : []);

  document.getElementById("research-workspace-summary").innerHTML = `
    <div class="research-summary-grid">
      <div class="research-summary-card">
        <span class="summary-label">Open assignments</span>
        <strong>${Number(research.open || 0)}</strong>
        <small>${Number(research.high_priority || 0)} high priority</small>
      </div>
      <div class="research-summary-card ${Number(research.high_priority || 0) ? "attention" : ""}">
        <span class="summary-label">High priority</span>
        <strong>${Number(research.high_priority || 0)}</strong>
        <small>Research follow-up requiring faster review</small>
      </div>
      <div class="research-summary-card">
        <span class="summary-label">Awaiting owner</span>
        <strong>${Number(research.awaiting_owner || 0)}</strong>
        <small>Completed findings waiting for a decision</small>
      </div>
      <div class="research-summary-card">
        <span class="summary-label">Coverage today</span>
        <strong>${Number(data.overview?.available || 0)}/${Number(data.overview?.tracked || 0)}</strong>
        <small>Tracked securities with usable data</small>
      </div>
    </div>
    <div class="research-conclusion-grid">
      <section class="research-conclusion-section">
        <span class="access-label">What Atlas currently concludes</span>
        ${leader ? `
          <div class="research-conclusion-row">
            <span class="thesis-badge ready">Leader</span>
            <div>
              <b class="row-title">${escapeHtml(leader.ticker)} leads the current research ranking at ${Number(leader.score).toFixed(1)}</b>
              <small class="row-meta">${escapeHtml(leader.sector || "Unclassified")} · ${escapeHtml(leader.category || "Tracked")}. A high Atlas score means stronger research priority, not an automatic purchase.</small>
            </div>
          </div>
        ` : `<div class="empty compact">Atlas does not have a current score conclusion.</div>`}
        ${strongestSector ? `
          <div class="research-conclusion-row">
            <span class="thesis-badge healthy">Sector</span>
            <div>
              <b class="row-title">${escapeHtml(strongestSector.sector)} has the strongest average daily move</b>
              <small class="row-meta">${signed(Number(strongestSector.average_change || 0))} across ${Number(strongestSector.securities || 0)} tracked securities.</small>
            </div>
          </div>
        ` : ""}
      </section>
      <section class="research-conclusion-section">
        <span class="access-label">Evidence changing now</span>
        ${mover ? `
          <div class="research-conclusion-row">
            <span class="thesis-badge ${Number(mover.percent_change || 0) >= 0 ? "healthy" : "exit"}">Move</span>
            <div>
              <b class="row-title">${escapeHtml(mover.ticker)} is the largest watchlist move at ${signed(Number(mover.percent_change || 0))}</b>
              <small class="row-meta">${escapeHtml(mover.sector || "Unclassified")}. A large move is a research trigger, not a recommendation by itself.</small>
            </div>
          </div>
        ` : `<div class="empty compact">No material watchlist movement is available.</div>`}
        ${weakestSector && weakestSector !== strongestSector ? `
          <div class="research-conclusion-row">
            <span class="thesis-badge watch">Watch</span>
            <div>
              <b class="row-title">${escapeHtml(weakestSector.sector)} has the weakest average daily move</b>
              <small class="row-meta">${signed(Number(weakestSector.average_change || 0))} across ${Number(weakestSector.securities || 0)} tracked securities.</small>
            </div>
          </div>
        ` : ""}
      </section>
    </div>
    <section class="research-assignment-section">
      <div class="research-assignment-head">
        <span class="access-label">Assigned follow-up</span>
        <button class="secondary-button" type="button" data-research-target="research-agenda-panel">Open full queue</button>
      </div>
      <div class="research-assignment-list">
        ${tasks.slice(0, 4).map(item => `
          <div class="research-assignment-row">
            <span class="role-chip">${escapeHtml(item.role || "Research")}</span>
            <div>
              <b class="row-title">${escapeHtml(item.subject || "Research assignment")}</b>
              <small class="row-meta">${escapeHtml(conciseText(item.prompt || "Atlas is awaiting research follow-up.", 190))}</small>
              <small class="row-meta task-age">Persistent assignment opened ${escapeHtml(researchTaskAgeLabel(item))}. Revalidate against current evidence before acting.</small>
            </div>
            <span class="tag ${String(item.priority || "").toLowerCase() === "high" ? "exit-tag" : ""}">${escapeHtml(item.priority || "normal")}</span>
          </div>
        `).join("") || `<div class="empty compact">No open research assignments.</div>`}
      </div>
    </section>
    <div class="research-summary-actions">
      <button class="secondary-button" type="button" data-research-target="research-scores-panel">View scores</button>
      <button class="secondary-button" type="button" data-research-target="research-movers-panel">View movers</button>
      <button class="secondary-button" type="button" data-research-target="research-sectors-panel">View sectors</button>
      <button class="secondary-button" type="button" data-research-target="research-actions-panel">View corporate actions</button>
    </div>
  `;
}

function renderReportArchive(reports) {
  reportArchive = reports;
  const visible = reports.filter(report => {
    if (reportArchiveFilter === "daily") return report.type === "Morning brief";
    if (reportArchiveFilter === "weekly") return report.type === "Weekly summary";
    return true;
  });
  const shown = reportArchiveExpanded ? visible : visible.slice(0, 6);
  const count = document.getElementById("report-result-count");
  if (count) {
    count.textContent = `Showing ${shown.length} of ${visible.length} reports`;
  }
  const toggle = document.getElementById("report-archive-toggle");
  toggle.hidden = visible.length <= 6;
  toggle.textContent = reportArchiveExpanded ? "Show recent only" : `Show all ${visible.length}`;
  document.querySelectorAll("[data-report-filter]").forEach(button => {
    const active = button.dataset.reportFilter === reportArchiveFilter;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  document.getElementById("report-archive").innerHTML = shown.map(report => {
    const generated = report.generated_at
      ? new Date(report.generated_at).toLocaleString([], {
          month: "short",
          day: "numeric",
          year: "numeric",
          hour: "numeric",
          minute: "2-digit",
        })
      : "Date unavailable";
    const evidence = report.coverage
      ? `${Number(report.coverage)} securities${report.leader?.ticker ? ` · Leader ${escapeHtml(report.leader.ticker)} ${Number(report.leader.score || 0).toFixed(1)}` : ""}`
      : report.type === "Weekly summary"
        ? "Seven-day research and paper evidence synthesis"
        : "Historical evidence is preserved in the full report";
    return `
      <article class="report-archive-row">
        <div class="report-archive-mark" aria-hidden="true">${report.type === "Weekly summary" ? "W" : "D"}</div>
        <div>
          <span class="access-label">${escapeHtml(report.type || "Atlas report")}</span>
          <b class="row-title">${escapeHtml(report.title || "Executive report")}</b>
          <small class="row-meta">${escapeHtml(generated)}</small>
          <small class="report-evidence">${evidence}</small>
        </div>
        <div class="report-archive-actions">
          <a class="secondary-button report-open-link" href="${escapeHtml(report.url || "#")}" target="_blank" rel="noopener">Open report</a>
          <button class="report-compare-link" type="button" data-research-target="research-priorities-panel">Compare current priorities</button>
        </div>
      </article>
    `;
  }).join("") || `<div class="empty compact">No ${escapeHtml(reportArchiveFilter === "all" ? "" : reportArchiveFilter)} reports are available in the recent archive.</div>`;
}

function renderScores(rows) {
  document.getElementById("score-leaders").innerHTML = rows.map((item, index) => `
    <article class="rank-row score-rank-row">
      <span class="rank-number">${index + 1}</span>
      <span><b class="row-title">${item.ticker}</b><small class="row-meta">${item.sector} · ${item.category}</small></span>
      <div class="score-rank-value">
        <strong class="atlas-score-badge ${atlasScoreTone(item.score)}">${Number(item.score).toFixed(0)}</strong>
        <small>${atlasScoreLabel(item.score)}</small>
      </div>
      <details class="score-explanation">
        <summary>Why this score</summary>
        ${renderScoreDrivers(item)}
      </details>
    </article>
  `).join("") || `<div class="empty">No score data available.</div>`;
}

function setRecommendationView(view) {
  recommendationView = ["actions", "buys", "exits", "universe"].includes(view)
    ? view
    : "actions";
  document.querySelectorAll("[data-recommendation-view]").forEach(button => {
    const active = button.dataset.recommendationView === recommendationView;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
  document.querySelectorAll("[data-recommendation-section]").forEach(section => {
    const sectionName = section.dataset.recommendationSection;
    section.hidden = recommendationView === "actions"
      ? sectionName === "universe"
      : sectionName !== recommendationView;
  });
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

function renderCorporateActions(rows) {
  document.getElementById("corporate-actions").innerHTML = rows.map(item => {
    const date = item.date ? new Date(item.date).toLocaleDateString() : "Date unavailable";
    return `
      <div class="action-row">
        <span>
          <b class="row-title">${escapeHtml(item.ticker)} &middot; ${escapeHtml(item.ratio)}</b>
          <small class="row-meta">${escapeHtml(item.type)} on ${escapeHtml(date)}</small>
        </span>
        <span class="integrity-status">${item.normalized ? "Normalized" : "Review"}</span>
      </div>`;
  }).join("") || `
    <div class="empty">No recent corporate actions detected in the current research universe.</div>`;
}

function renderPaperWorkspaceSummary(paper) {
  {
    const simplePositions = Array.isArray(paper.positions) ? paper.positions : [];
    const simpleActivity = Array.isArray(paper.activity) ? paper.activity : [];
    const simpleFocus = paper.portfolio_focus || {};
    const simpleHighlights = Array.isArray(simpleFocus.highlights)
      ? simpleFocus.highlights.filter(item =>
          ["watch", "trim", "exit"].includes(String(item.label || "").toLowerCase())
        ).slice(0, 3)
      : [];
    const simpleLatestAction = simpleActivity[0] || null;
    document.getElementById("paper-workspace-summary").innerHTML = `
      <div class="paper-summary-grid simplified">
        <div class="paper-summary-card result">
          <span class="summary-label">Portfolio value</span>
          <strong>${paper.configured ? money.format(Number(paper.equity || 0)) : "--"}</strong>
          <small>Simulated account</small>
        </div>
        <div class="paper-summary-card ${changeClass(Number(paper.total_return_pct || 0))}">
          <span class="summary-label">Total return</span>
          <strong>${paper.configured ? signed(Number(paper.total_return_pct || 0)) : "--"}</strong>
          <small>Since paper tracking began</small>
        </div>
        <div class="paper-summary-card">
          <span class="summary-label">Cash</span>
          <strong>${paper.configured ? money.format(Number(paper.cash || 0)) : "--"}</strong>
          <small>Available simulated capital</small>
        </div>
        <div class="paper-summary-card">
          <span class="summary-label">Open positions</span>
          <strong>${simplePositions.length}</strong>
          <small>${simpleHighlights.length} need attention</small>
        </div>
      </div>
      <div class="paper-priority-grid simplified">
        <section class="paper-priority-section">
          <span class="access-label">Needs attention</span>
          <div class="paper-priority-list">
            ${simpleHighlights.map(item => `
              <div class="paper-priority-row">
                <span class="thesis-badge ${escapeHtml(item.label || "watch")}">${escapeHtml(item.label || "watch")}</span>
                <div>
                  <b class="row-title">${escapeHtml(item.ticker || "Holding")}</b>
                  <small class="row-meta">${escapeHtml(item.summary || "Atlas recommends review.")}</small>
                </div>
                <button class="link-button" type="button" data-paper-target="${escapeHtml(item.anchor_id || "")}">Open</button>
              </div>
            `).join("") || `<div class="empty compact">No positions need attention.</div>`}
          </div>
        </section>
        <section class="paper-priority-section">
          <span class="access-label">Latest paper activity</span>
          ${simpleLatestAction ? `
            <div class="latest-paper-action">
              <span class="tag ${simpleLatestAction.side === "sell" ? "exit-tag" : "buy-tag"}">${escapeHtml(String(simpleLatestAction.action_label || simpleLatestAction.side || "trade").replaceAll("_", " "))}</span>
              <div>
                <b class="row-title">${escapeHtml(simpleLatestAction.title || `${simpleLatestAction.ticker || "Atlas"} paper action`)}</b>
                <small class="row-meta">${new Date(simpleLatestAction.timestamp).toLocaleString()} · ${Number(simpleLatestAction.shares || 0).toFixed(2)} shares at ${money.format(Number(simpleLatestAction.fill_price) || 0)}</small>
                <small class="row-meta">${escapeHtml(conciseText(simpleLatestAction.summary || "Atlas recorded a simulated trade.", 120))}</small>
              </div>
            </div>
          ` : `<div class="empty compact">No simulated trades recorded yet.</div>`}
        </section>
      </div>
    `;
  }
  const positions = Array.isArray(paper.positions) ? paper.positions : [];
  const activity = Array.isArray(paper.activity) ? paper.activity : [];
  const focus = paper.portfolio_focus || {};
  const highlights = Array.isArray(focus.highlights) ? focus.highlights : [];
  const counts = focus.counts || {};
  const actionCount = Number(counts.watch || 0) + Number(counts.trim || 0) + Number(counts.exit || 0);
  const latestAction = activity[0] || null;
  const validation = paper.validation_summary || {};
  const readiness = validation.capital_readiness || {};
  const readinessPassed = Array.isArray(readiness.criteria)
    ? readiness.criteria.filter(item => item.passed).length
    : 0;
  const readinessTotal = Array.isArray(readiness.criteria) ? readiness.criteria.length : 0;
  const readinessProgress = Math.max(0, Math.min(100, Number(readiness.progress_pct) || 0));
  const nextMilestones = Array.isArray(readiness.next_milestones)
    ? readiness.next_milestones
    : [];
  const evidencePipeline = validation.evidence_pipeline || {};
  const completedDiagnostics = validation.completed_position_diagnostics || {};
  const completedCycles = Array.isArray(completedDiagnostics.cycles)
    ? completedDiagnostics.cycles
    : [];
  const shadowAnalysis = validation.shadow_trigger_analysis || {};
  const shadowCandidates = Array.isArray(shadowAnalysis.candidates)
    ? shadowAnalysis.candidates
    : [];
  const prospectiveTracker = validation.prospective_review_tracker || {};
  const prospectiveSignals = Array.isArray(prospectiveTracker.signals)
    ? prospectiveTracker.signals
    : [];
  const prospectiveCounts = prospectiveTracker.counts || {};
  const prospectivePriorityCounts =
    prospectiveTracker.review_priority_counts || {};
  const latestPriorityEscalations = Array.isArray(
    prospectiveTracker.latest_priority_escalations
  )
    ? prospectiveTracker.latest_priority_escalations
    : [];
  const escalationEpisodeEvidence =
    prospectiveTracker.escalation_episode_evidence || {};
  const escalationEpisodes = Array.isArray(
    escalationEpisodeEvidence.episodes
  )
    ? escalationEpisodeEvidence.episodes
    : [];
  const prospectiveEffectiveness =
    validation.prospective_review_effectiveness || {};
  const effectivenessGates = Array.isArray(prospectiveEffectiveness.gates)
    ? prospectiveEffectiveness.gates
    : [];
  const effectivenessComparison =
    prospectiveEffectiveness.outcome_comparison || {};
  const effectivenessOutcomes = Array.isArray(
    prospectiveEffectiveness.outcomes
  )
    ? prospectiveEffectiveness.outcomes
    : [];
  const latestEvidenceSnapshot = evidencePipeline.latest_snapshot_at
    ? new Date(evidencePipeline.latest_snapshot_at).toLocaleString()
    : "No snapshot recorded";

  document.getElementById("paper-evidence-detail").innerHTML = `
    <div class="paper-summary-grid">
      <div class="paper-summary-card result">
        <span class="summary-label">Simulated equity</span>
        <strong>${paper.configured ? money.format(Number(paper.equity || 0)) : "--"}</strong>
        <small class="${changeClass(Number(paper.total_return_pct || 0))}">${paper.configured ? `${signed(Number(paper.total_return_pct || 0))} total return` : "Paper account unavailable"}</small>
      </div>
      <div class="paper-summary-card">
        <span class="summary-label">Open holdings</span>
        <strong>${positions.length}</strong>
        <small>${money.format(Number(paper.cash || 0))} simulated cash available</small>
      </div>
      <div class="paper-summary-card ${actionCount ? "attention" : "steady"}">
        <span class="summary-label">Need attention</span>
        <strong>${actionCount}</strong>
        <small>${actionCount ? `${Number(counts.exit || 0)} exit, ${Number(counts.trim || 0)} trim, ${Number(counts.watch || 0)} watch` : "No position exceptions"}</small>
      </div>
      <div class="paper-summary-card">
        <span class="summary-label">Stage 5 evidence</span>
        <strong>${readinessTotal ? `${readinessPassed}/${readinessTotal}` : "--"}</strong>
        <small>${escapeHtml(readiness.status_label || validation.status_label || "Evidence building")}${readinessTotal ? ` · ${readinessProgress.toFixed(1)}% evidence maturity` : ""}</small>
      </div>
    </div>
    <div class="paper-priority-grid">
      <section class="paper-priority-section">
        <span class="access-label">Positions requiring attention</span>
        <div class="paper-priority-list">
          ${highlights.filter(item => ["watch", "trim", "exit"].includes(String(item.label || "").toLowerCase())).slice(0, 4).map(item => `
            <div class="paper-priority-row">
              <span class="thesis-badge ${escapeHtml(item.label || "watch")}">${escapeHtml(item.label || "watch")}</span>
              <div>
                <b class="row-title">${escapeHtml(item.ticker || "Holding")}</b>
                <small class="row-meta">${escapeHtml(item.summary || "Atlas recommends review.")}</small>
              </div>
              <button class="link-button" type="button" data-paper-target="${escapeHtml(item.anchor_id || "")}">Review</button>
            </div>
          `).join("") || `<div class="empty compact">No simulated holdings currently require attention.</div>`}
        </div>
      </section>
      <section class="paper-priority-section">
        <span class="access-label">Latest simulated action</span>
        ${latestAction ? `
          <div class="latest-paper-action">
            <span class="tag ${latestAction.side === "sell" ? "exit-tag" : "buy-tag"}">${escapeHtml(String(latestAction.action_label || latestAction.side || "trade").replaceAll("_", " "))}</span>
            <div>
              <b class="row-title">${escapeHtml(latestAction.title || `${latestAction.ticker || "Atlas"} paper action`)}</b>
              <small class="row-meta">${new Date(latestAction.timestamp).toLocaleString()} · ${Number(latestAction.shares || 0).toFixed(2)} shares at ${money.format(Number(latestAction.fill_price) || 0)}</small>
              <small class="row-meta">${escapeHtml(conciseText(latestAction.summary || "Atlas recorded a simulated trade.", 170))}</small>
            </div>
          </div>
        ` : `<div class="empty compact">No simulated purchases or sales have been recorded yet.</div>`}
      </section>
    </div>
    <section class="paper-evidence-pipeline">
      <div class="paper-evidence-heading">
        <div>
          <span class="access-label">Evidence pipeline</span>
          <b>${escapeHtml(evidencePipeline.headline || "Atlas is preparing its paper-decision evidence.")}</b>
        </div>
        <span>${escapeHtml(evidencePipeline.source || "Active paper ledger")}</span>
      </div>
      <div class="paper-pipeline-grid">
        <div>
          <span>Latest snapshot</span>
          <strong>${escapeHtml(latestEvidenceSnapshot)}</strong>
          <small>${Number(evidencePipeline.snapshot_count || 0)} benchmark-aware observations</small>
        </div>
        <div>
          <span>Executed decisions</span>
          <strong>${Number(evidencePipeline.executed_decisions || 0)}</strong>
          <small>Simulated fills available for evaluation</small>
        </div>
        <div>
          <span>Judged coverage</span>
          <strong>${Number(evidencePipeline.judgment_coverage_pct || 0).toFixed(1)}%</strong>
          <small>${Number(evidencePipeline.judged_decisions || 0)} judged &middot; ${Number(evidencePipeline.awaiting_judgment || 0)} waiting</small>
        </div>
        <div>
          <span>Completed positions</span>
          <strong>${Number(evidencePipeline.completed_positions || evidencePipeline.realized_exits || 0)}</strong>
          <small>${Number(evidencePipeline.partial_trims || 0)} partial trims reported separately</small>
        </div>
      </div>
      <small class="paper-evidence-note">${escapeHtml(evidencePipeline.next_action || "Keep the scheduled paper cycle running.")}</small>
    </section>
    ${completedDiagnostics.available ? `
      <section class="paper-loss-diagnostic">
        <div class="paper-evidence-heading">
          <div>
            <span class="access-label">Completed position diagnosis</span>
            <b>${escapeHtml(completedDiagnostics.headline || "Atlas is reviewing completed paper outcomes.")}</b>
            <small>${escapeHtml(completedDiagnostics.primary_finding || "")}</small>
          </div>
          <span>${Number(completedDiagnostics.sample_size || 0)} completed</span>
        </div>
        <div class="paper-diagnostic-metrics">
          <div><span>Late risk response</span><strong>${Number(completedDiagnostics.late_risk_responses || 0)}/${Number(completedDiagnostics.losses || 0)}</strong></div>
          <div><span>Sharp-decline entries</span><strong>${Number(completedDiagnostics.sharp_decline_entries || 0)}</strong></div>
          <div><span>Fragmented exits</span><strong>${Number(completedDiagnostics.fragmented_exits || 0)}</strong></div>
          <div><span>Average completed loss</span><strong class="negative">${signed(Number(completedDiagnostics.average_loss_pct || 0))}</strong></div>
        </div>
        <div class="paper-cycle-list">
          ${completedCycles.map(item => `
            <article class="paper-cycle-row">
              <div class="paper-cycle-result">
                <b>${escapeHtml(item.ticker || "Position")}</b>
                <strong class="${changeClass(Number(item.realized_gain_loss || 0))}">${money.format(Number(item.realized_gain_loss || 0))}</strong>
                <small>${signed(Number(item.realized_return_pct || 0))} over ${Number(item.holding_days || 0).toFixed(1)} days</small>
              </div>
              <div>
                <span>Entry</span>
                <small>${escapeHtml(item.entry?.finding || "Entry evidence unavailable.")}</small>
              </div>
              <div>
                <span>First defensive action</span>
                <small>${escapeHtml(item.risk_response?.finding || "Risk-response evidence unavailable.")} Day ${Number(item.days_to_first_risk_action || 0).toFixed(1)}.</small>
              </div>
              <div>
                <span>Exit execution</span>
                <small>${escapeHtml(item.execution?.finding || "Exit evidence unavailable.")}</small>
              </div>
            </article>
          `).join("")}
        </div>
        <small class="paper-evidence-note">${escapeHtml(completedDiagnostics.sample_warning || "This remains early simulated evidence.")}</small>
      </section>
    ` : ""}
    ${shadowAnalysis.available ? `
      <section class="paper-shadow-analysis">
        <div class="paper-evidence-heading">
          <div>
            <span class="access-label">Defensive trigger shadow test</span>
            <b>${escapeHtml(shadowAnalysis.headline || "Atlas tested earlier defensive signals without changing policy.")}</b>
            <small>${escapeHtml(shadowAnalysis.detail || "This is a no-action historical replay.")}</small>
          </div>
          <span class="paper-policy-badge">No policy change</span>
        </div>
        <div class="paper-shadow-candidates">
          ${shadowCandidates.map(candidate => {
            const improvement = Number(candidate.completed_improvement || 0);
            const decision = String(candidate.decision || "study").toLowerCase();
            return `
              <article class="paper-shadow-card ${escapeHtml(decision)}">
                <div class="paper-shadow-card-heading">
                  <div>
                    <span>${escapeHtml(candidate.action || "Shadow test")}</span>
                    <b>${escapeHtml(candidate.label || "Defensive candidate")}</b>
                  </div>
                  <strong>${escapeHtml(candidate.decision_label || "Continue study")}</strong>
                </div>
                <p>${escapeHtml(candidate.conclusion || "Atlas needs more simulated evidence.")}</p>
                <div class="paper-shadow-threshold">
                  <span>Trigger tested</span>
                  <b>${signed(Number(candidate.loss_threshold_pct || 0))} position return and ${signed(Number(candidate.lag_threshold_pct || 0))} lag</b>
                </div>
                <div class="paper-shadow-metrics">
                  <div><span>Triggered cycles</span><strong>${Number(candidate.triggered_cycles || 0)}</strong></div>
                  <div><span>Later recovered</span><strong>${Number(candidate.recovered_cycles || 0)} (${Number(candidate.recovery_rate_pct || 0).toFixed(1)}%)</strong></div>
                  <div><span>Actual completed result</span><strong class="${changeClass(Number(candidate.actual_completed_gain_loss || 0))}">${money.format(Number(candidate.actual_completed_gain_loss || 0))}</strong></div>
                  <div><span>Shadow difference</span><strong class="${changeClass(improvement)}">${improvement >= 0 ? "+" : ""}${money.format(improvement)}</strong></div>
                </div>
              </article>
            `;
          }).join("")}
        </div>
        <small class="paper-evidence-note">${escapeHtml(shadowAnalysis.sample_warning || "Keep collecting paper evidence before changing strategy.")} “Recovered” means the observed price later rose above the tested trigger price; it does not guarantee a profitable position.</small>
      </section>
    ` : ""}
    ${prospectiveTracker.available ? `
      <section class="paper-prospective-tracker">
        <div class="paper-evidence-heading">
          <div>
            <span class="access-label">Prospective review tracker</span>
            <b>${escapeHtml(prospectiveTracker.headline || "Atlas is preparing forward-only signal tracking.")}</b>
            <small>${escapeHtml(prospectiveTracker.detail || "This tracker observes signals without taking action.")}</small>
          </div>
          <span class="paper-review-only-badge">Review only</span>
        </div>
        <div class="paper-prospective-summary">
          <div>
            <span>Study status</span>
            <strong>${prospectiveTracker.activated ? "Active" : "Starts next snapshot"}</strong>
          </div>
          <div>
            <span>Trigger observed</span>
            <strong>${signed(Number(prospectiveTracker.loss_threshold_pct || -2))} return + ${signed(Number(prospectiveTracker.lag_threshold_pct || -3))} lag</strong>
          </div>
          <div>
            <span>Needs attention</span>
            <strong>${Number(prospectivePriorityCounts.urgent || 0) + Number(prospectivePriorityCounts.monitor || 0)}</strong>
          </div>
          <div>
            <span>New reviews</span>
            <strong>${Number(prospectiveCounts.active || 0)}</strong>
          </div>
          <div>
            <span>Persistent weakness</span>
            <strong>${Number(prospectiveCounts.persistent_weakness || 0)}</strong>
          </div>
          <div>
            <span>Recovered</span>
            <strong>${Number(prospectiveCounts.recovered || 0)}</strong>
          </div>
        </div>
        <div class="paper-priority-escalation-strip ${latestPriorityEscalations.length ? "active" : "clear"}">
          <div>
            <span>Priority escalation watch</span>
            <strong>${latestPriorityEscalations.length ? `${latestPriorityEscalations.length} signal${latestPriorityEscalations.length === 1 ? "" : "s"} moved into elevated attention` : "No new elevated-priority changes"}</strong>
            <small>Only upward crossings into Monitor closely or Review now appear here. Routine score drift is omitted.</small>
          </div>
          ${latestPriorityEscalations.length ? `<div class="paper-priority-escalation-list">${latestPriorityEscalations.map(item => `<span><b>${escapeHtml(item.ticker || "Holding")}</b> ${escapeHtml(item.previous_review_priority_label || "Prior level")} → ${escapeHtml(item.review_priority_label || "Elevated")} · ${Number(item.review_priority_score || 0)}/100</span>`).join("")}</div>` : `<span class="paper-priority-escalation-clear">Clear</span>`}
        </div>
        <div class="paper-escalation-duration">
          <div class="paper-escalation-duration-heading">
            <div>
              <span>Elevated episode evidence</span>
              <strong>${escalationEpisodes.length ? `${Number(escalationEpisodeEvidence.open_episode_count || 0)} open · ${Number(escalationEpisodeEvidence.resolved_episode_count || 0)} resolved` : "No elevated warning episodes recorded yet"}</strong>
              <small>Tracks elapsed days, scheduled observations, peak priority, and resolution after a warning becomes elevated.</small>
            </div>
            <span>${escalationEpisodeEvidence.average_resolved_duration_days == null ? "Building history" : `${Number(escalationEpisodeEvidence.average_resolved_duration_days).toFixed(1)} day average resolution`}</span>
          </div>
          ${escalationEpisodes.length ? `<div class="paper-escalation-episode-list">${escalationEpisodes.slice(0, 4).map(item => `
            <div class="paper-escalation-episode-row ${item.open ? "open" : escapeHtml(item.resolution || "resolved")}">
              <div><b>${escapeHtml(item.ticker || "Holding")}</b><span>${escapeHtml(item.resolution_label || "Elevated episode")}</span></div>
              <div><span>Duration</span><strong>${item.duration_days == null ? "--" : `${Number(item.duration_days).toFixed(1)} days`}</strong><small>${Number(item.snapshots_open || 0)} scheduled observation${Number(item.snapshots_open || 0) === 1 ? "" : "s"}</small></div>
              <div><span>Peak priority</span><strong>${escapeHtml(item.peak_review_priority_label || "Elevated")}</strong><small>${Number(item.peak_review_priority_score || 0)}/100</small></div>
            </div>
          `).join("")}</div>` : `<small class="paper-escalation-duration-empty">The first meaningful move into Monitor closely or Review now will start this clock.</small>`}
          <small class="paper-evidence-note">Episode duration is observational evidence. It cannot trigger or time a simulated sale.</small>
        </div>
        <div class="paper-prospective-list">
          ${prospectiveSignals.map(signal => `
            <article class="paper-prospective-row ${escapeHtml(signal.status || "active")}">
              <div>
                <b>${escapeHtml(signal.ticker || "Holding")}</b>
                <span>${escapeHtml(signal.status_label || "Review signal")}</span>
                <strong class="paper-review-priority ${escapeHtml(signal.review_priority || "low")}">${escapeHtml(signal.review_priority_label || "Low priority")} · ${Number(signal.review_priority_score || 0)}/100</strong>
              </div>
              <div>
                <span>Triggered</span>
                <strong>${signed(Number(signal.trigger_return_pct || 0))} return</strong>
                <small>${signed(Number(signal.trigger_lag_pct || 0))} benchmark lag</small>
              </div>
              <div>
                <span>Latest observation</span>
                <strong>${signed(Number(signal.latest_return_pct || 0))} return</strong>
                <small>${Number(signal.snapshots_observed || 0)} snapshot${Number(signal.snapshots_observed || 0) === 1 ? "" : "s"} followed</small>
              </div>
              <div>
                <span>Why this priority</span>
                <small>${escapeHtml((Array.isArray(signal.review_priority_rationale) ? signal.review_priority_rationale : []).join(" ") || "Atlas needs more observations to rank this review.")}</small>
              </div>
            </article>
          `).join("") || `
            <div class="empty compact">
              ${prospectiveTracker.activated
                ? "No holding has met the prospective review threshold since tracking began."
                : "The next scheduled paper snapshot will activate this forward-only study."}
            </div>
          `}
        </div>
        <small class="paper-evidence-note">Priority ranks owner attention only. Escalation notices cannot place or force a simulated trade, and they do not change paper policy. A recovered signal only means price later moved above its trigger price.</small>
      </section>
    ` : ""}
    ${prospectiveEffectiveness.available ? `
      <section class="paper-effectiveness-scorecard">
        <div class="paper-evidence-heading">
          <div>
            <span class="access-label">Review signal effectiveness</span>
            <b>${escapeHtml(prospectiveEffectiveness.headline || "Atlas is collecting forward evidence.")}</b>
            <small>${escapeHtml(prospectiveEffectiveness.detail || "The scorecard separates confirmed weakness from false alarms.")}</small>
          </div>
          <span class="paper-effectiveness-status ${escapeHtml(prospectiveEffectiveness.status || "collecting")}">${escapeHtml(prospectiveEffectiveness.status_label || "Collecting evidence")}</span>
        </div>
        <div class="paper-effectiveness-metrics">
          <div><span>Resolved signals</span><strong>${Number(prospectiveEffectiveness.resolved_signals || 0)}</strong></div>
          <div><span>Confirmed weakness</span><strong>${Number(prospectiveEffectiveness.confirmed_weakness || 0)}</strong></div>
          <div><span>False alarms</span><strong>${Number(prospectiveEffectiveness.false_alarms || 0)}</strong></div>
          <div><span>Confirmation rate</span><strong>${prospectiveEffectiveness.confirmation_rate_pct == null ? "--" : `${Number(prospectiveEffectiveness.confirmation_rate_pct).toFixed(1)}%`}</strong></div>
          <div><span>Evidence progress</span><strong>${Number(prospectiveEffectiveness.evidence_progress_pct || 0).toFixed(1)}%</strong></div>
        </div>
        ${effectivenessOutcomes.length ? `
          <div class="paper-signal-comparison">
            <div class="paper-signal-comparison-heading">
              <div>
                <span class="access-label">What happened after each warning</span>
                <b>Confirmed weakness versus recovery risk</b>
              </div>
              <small>${effectivenessComparison.outcome_separation_pct == null
                ? "Waiting for both outcome types"
                : `${Number(effectivenessComparison.outcome_separation_pct).toFixed(2)} point outcome separation`}</small>
            </div>
            <div class="paper-signal-comparison-metrics">
              <div>
                <span>Confirmed warnings</span>
                <strong class="${changeClass(Number(effectivenessComparison.confirmed_avg_post_trigger_move_pct || 0))}">${signed(effectivenessComparison.confirmed_avg_post_trigger_move_pct)}</strong>
                <small>average move since warning</small>
              </div>
              <div>
                <span>False alarms / recoveries</span>
                <strong class="${changeClass(Number(effectivenessComparison.false_alarm_avg_post_trigger_move_pct || 0))}">${signed(effectivenessComparison.false_alarm_avg_post_trigger_move_pct)}</strong>
                <small>average move since warning</small>
              </div>
              <div>
                <span>Benchmark-adjusted separation</span>
                <strong>${effectivenessComparison.benchmark_adjusted_separation_pct == null ? "--" : `${Number(effectivenessComparison.benchmark_adjusted_separation_pct).toFixed(2)} pts`}</strong>
                <small>separation after the stronger SPY or QQQ move</small>
              </div>
            </div>
            <div class="paper-signal-timing">
              <div>
                <span>Confirmed outcome span</span>
                <strong>${effectivenessComparison.confirmed_avg_warning_span_snapshots == null ? "--" : `${Number(effectivenessComparison.confirmed_avg_warning_span_snapshots).toFixed(1)} snapshots`}</strong>
                <small>${effectivenessComparison.confirmed_avg_warning_span_days == null ? "Waiting for timing evidence" : `${Number(effectivenessComparison.confirmed_avg_warning_span_days).toFixed(1)} average days observed`}</small>
              </div>
              <div>
                <span>Recovery first appeared</span>
                <strong>${effectivenessComparison.false_alarm_avg_snapshots_to_recovery == null ? "--" : `${Number(effectivenessComparison.false_alarm_avg_snapshots_to_recovery).toFixed(1)} snapshots`}</strong>
                <small>${effectivenessComparison.false_alarm_avg_days_to_recovery == null ? "No recovery timing yet" : `${Number(effectivenessComparison.false_alarm_avg_days_to_recovery).toFixed(1)} average days after warning`}</small>
              </div>
              <div>
                <span>Recovery durability gap</span>
                <strong>${effectivenessComparison.recovery_durability_separation_pct == null ? "--" : `${Number(effectivenessComparison.recovery_durability_separation_pct).toFixed(1)} pts`}</strong>
                <small>${effectivenessComparison.false_alarm_avg_recovery_durability_pct == null ? "Waiting for durability evidence" : `${Number(effectivenessComparison.false_alarm_avg_recovery_durability_pct).toFixed(1)}% recovery vs ${Number(effectivenessComparison.confirmed_avg_recovery_durability_pct || 0).toFixed(1)}% confirmed`}</small>
              </div>
            </div>
            <div class="paper-signal-outcomes">
              ${effectivenessOutcomes.map(outcome => `
                <article class="paper-signal-outcome ${escapeHtml(outcome.classification || "open")}">
                  <div>
                    <b>${escapeHtml(outcome.ticker || "Holding")}</b>
                    <span>${escapeHtml(outcome.classification_label || outcome.status_label || "Review outcome")}</span>
                    <small>${escapeHtml(outcome.benchmark_attribution_label || "Benchmark context unavailable")}</small>
                    <small>${escapeHtml(outcome.recovery_quality_label || "Recovery quality unavailable")}</small>
                  </div>
                  <dl>
                    <div><dt>Since warning</dt><dd class="${changeClass(Number(outcome.post_trigger_move_pct || 0))}">${signed(outcome.post_trigger_move_pct)}</dd></div>
                    <div><dt>Worst after</dt><dd class="${changeClass(Number(outcome.worst_post_trigger_move_pct || 0))}">${signed(outcome.worst_post_trigger_move_pct)}</dd></div>
                    <div><dt>Best recovery</dt><dd class="${changeClass(Number(outcome.best_post_trigger_move_pct || 0))}">${signed(outcome.best_post_trigger_move_pct)}</dd></div>
                    <div><dt>Stronger benchmark</dt><dd>${escapeHtml(outcome.comparison_benchmark || "--")} ${signed(outcome.comparison_benchmark_move_pct)}</dd></div>
                    <div><dt>Vs benchmark</dt><dd class="${changeClass(Number(outcome.benchmark_relative_move_pct || 0))}">${signed(outcome.benchmark_relative_move_pct)}</dd></div>
                    <div><dt>Warning span</dt><dd>${Number(outcome.snapshots_observed || 0)} snapshots / ${Number(outcome.warning_span_days || 0).toFixed(1)} days</dd></div>
                    <div><dt>First above trigger</dt><dd>${outcome.snapshots_to_first_recovery == null ? "Not observed" : `${Number(outcome.snapshots_to_first_recovery)} snapshots / ${Number(outcome.days_to_first_recovery || 0).toFixed(1)} days`}</dd></div>
                    <div><dt>Recovery quality</dt><dd>${outcome.recovery_durability_pct == null ? "--" : `${Number(outcome.recovery_durability_pct).toFixed(1)}% above / ${Number(outcome.relapse_count || 0)} relapse${Number(outcome.relapse_count || 0) === 1 ? "" : "s"}`}</dd></div>
                  </dl>
                </article>
              `).join("")}
            </div>
            <small class="paper-signal-disclosure">These are observed price paths after a review signal, not hypothetical fill results. Benchmark context uses the stronger SPY or QQQ move over the same period; it does not claim the benchmark caused the stock move. A first move above the trigger can be temporary and does not resolve the warning. Atlas measures sustained recovery and relapse frequency before drawing a conclusion. This evidence cannot execute a sale.</small>
          </div>
        ` : ""}
        <div class="paper-effectiveness-gates">
          ${effectivenessGates.map(gate => {
            const progress = Math.max(0, Math.min(100, Number(gate.progress_pct || 0)));
            const current = gate.current == null ? "--" : Number(gate.current).toFixed(gate.id === "confirmation_quality" ? 1 : 0);
            const target = Number(gate.target || 0).toFixed(gate.id === "confirmation_quality" ? 1 : 0);
            return `
              <div class="paper-effectiveness-gate ${gate.passed ? "passed" : ""}">
                <div>
                  <b>${escapeHtml(gate.label || "Evidence gate")}</b>
                  <small>${current}${gate.id === "confirmation_quality" && gate.current != null ? "%" : ""} now · target ${target}${gate.id === "confirmation_quality" ? "%" : ""}</small>
                </div>
                <div class="paper-evidence-progress">
                  <span>${progress.toFixed(1)}%</span>
                  <div class="progress-track"><i style="width:${progress}%"></i></div>
                </div>
              </div>
            `;
          }).join("")}
        </div>
        <small class="paper-evidence-note">${escapeHtml(prospectiveEffectiveness.next_action || "Keep collecting forward outcomes.")} Passing these gates permits owner review only; it does not change paper or real-trading authority.</small>
      </section>
    ` : ""}
    <section class="paper-evidence-roadmap">
      <div class="paper-evidence-heading">
        <div>
          <span class="access-label">What Stage 5 needs next</span>
          <b>${escapeHtml(readiness.headline || "Atlas is collecting evidence before any real-capital discussion.")}</b>
        </div>
        <span>${readinessPassed}/${readinessTotal || 0} gates pass</span>
      </div>
      <div class="paper-evidence-list">
        ${nextMilestones.map(item => {
          const progress = Math.max(0, Math.min(100, Number(item.progress_pct) || 0));
          return `
            <div class="paper-evidence-row">
              <div>
                <b>${escapeHtml(item.label || "Evidence milestone")}</b>
                <small>${escapeHtml(item.current || "N/A")} now · target ${escapeHtml(item.target || "")}</small>
                <small>${escapeHtml(item.next_step || "Continue the paper evaluation.")}</small>
              </div>
              <div class="paper-evidence-progress">
                <span>${progress.toFixed(1)}%</span>
                <div class="progress-track"><i style="width:${progress}%"></i></div>
              </div>
            </div>
          `;
        }).join("") || `<div class="empty compact">Atlas will identify the next evidence milestones after paper tracking begins.</div>`}
      </div>
      <small class="paper-evidence-note">Evidence maturity measures progress toward conservative proof gates. It is not a time estimate and cannot enable real trading.</small>
    </section>
    <div class="paper-summary-actions">
      <button class="secondary-button" type="button" data-paper-section="paper-positions-panel">View holdings</button>
      <button class="secondary-button" type="button" data-paper-section="paper-activity-panel">View recent activity</button>
      <button class="secondary-button" type="button" data-paper-section="paper-learning-panel">View Stage 5 evidence</button>
    </div>
  `;
}

function renderThesisOverview(overview) {
  const counts = overview.counts || {};
  const attention = overview.attention || [];
  document.getElementById("thesis-overview").innerHTML = `
    <div class="thesis-counts">
      ${["healthy", "watch", "trim", "exit"].map(label => `
        <div class="thesis-count-card">
          <span class="thesis-badge ${label}">${label}</span>
          <strong>${Number(counts[label] || 0).toFixed(0)}</strong>
        </div>
      `).join("")}
    </div>
    <div class="thesis-attention">
      <span class="access-label">Needs attention first</span>
      <div class="thesis-attention-list">
        ${attention.length ? attention.map(item => `
          <div class="thesis-attention-row">
            <span class="thesis-badge ${escapeHtml(item.label)}">${escapeHtml(item.label)}</span>
            <div>
              <b class="row-title">${escapeHtml(item.ticker || "Holding")}</b>
              <small class="row-meta">${escapeHtml(item.summary || "")}</small>
            </div>
          </div>
        `).join("") : `<div class="empty">No open simulated positions.</div>`}
      </div>
    </div>
  `;
}

function renderPortfolioFocus(focus) {
  const counts = focus.counts || {};
  const highlights = focus.highlights || [];
  document.getElementById("portfolio-focus").innerHTML = `
    <div class="portfolio-focus-summary">
      <span class="access-label">Portfolio action readout</span>
      <strong>${escapeHtml(focus.headline || "Atlas is collecting paper-position context.")}</strong>
      <div class="portfolio-focus-counts">
        ${["healthy", "watch", "trim", "exit"].map(label => `
          <div class="portfolio-focus-count">
            <span class="thesis-badge ${label}">${label}</span>
            <strong>${Number(counts[label] || 0).toFixed(0)}</strong>
          </div>
        `).join("")}
      </div>
    </div>
    <div class="portfolio-focus-list">
      <span class="access-label">Priority holdings</span>
      ${highlights.length ? highlights.slice(0, 2).map(item => `
        <div class="portfolio-focus-row">
          <span class="thesis-badge ${escapeHtml(item.label || "healthy")}">${escapeHtml(item.label || "healthy")}</span>
          <div>
            <b class="row-title">${escapeHtml(item.ticker || "Holding")}</b>
            <small class="row-meta">${escapeHtml(item.summary || "")}</small>
            ${item.anchor_id ? `<small class="row-meta"><button type="button" class="inline-jump" data-paper-target="${escapeHtml(item.anchor_id)}">Open holding</button></small>` : ""}
          </div>
          <small class="row-meta ${changeClass(item.unrealized_gain_loss)}">${money.format(Number(item.unrealized_gain_loss) || 0)}</small>
        </div>
      `).join("") : `<div class="empty">No open simulated positions.</div>`}
    </div>
  `;
}

function renderPositionLadder(rows) {
  document.getElementById("position-ladder").innerHTML = rows.map(item => `
    <div class="ladder-card ${escapeHtml(item.id || "healthy")}">
      <div class="ladder-card-head">
        <span class="thesis-badge ${escapeHtml(item.id || "healthy")}">${escapeHtml(item.label || "Hold steady")}</span>
        <strong>${Number(item.count || 0).toFixed(0)}</strong>
      </div>
      <p>${escapeHtml(item.detail || "")}</p>
      <div class="ladder-list">
        ${(item.items || []).length ? item.items.map(position => `
          <div class="ladder-row">
            <div>
              <b class="row-title">${escapeHtml(position.ticker || "Holding")}</b>
              <small class="row-meta">${escapeHtml(position.summary || "")}</small>
            </div>
            <small class="row-meta ${changeClass(position.unrealized_gain_loss)}">${money.format(Number(position.unrealized_gain_loss) || 0)}</small>
          </div>
        `).join("") : `<div class="empty compact">No positions in this group.</div>`}
      </div>
    </div>
  `).join("");
}

function renderPositions(rows) {
  paperPositions = Array.isArray(rows) ? rows : [];
  const priority = { exit: 0, trim: 1, watch: 2, healthy: 3 };
  const ordered = paperPositions.slice().sort((left, right) => {
    const leftLabel = String(left.thesis_status?.label || "healthy").toLowerCase();
    const rightLabel = String(right.thesis_status?.label || "healthy").toLowerCase();
    return (priority[leftLabel] ?? 4) - (priority[rightLabel] ?? 4) ||
      Number(left.unrealized_gain_loss || 0) - Number(right.unrealized_gain_loss || 0);
  });
  document.getElementById("positions").innerHTML = ordered.map(item => {
    const review = item.review || {};
    const thesis = item.thesis_status || { label: "healthy", summary: "Awaiting the next daily thesis review." };
    const memory = item.research_memory || null;
    const journal = item.decision_journal || [];
    return `
      <div class="position-row" id="${escapeHtml(item.anchor_id || "")}">
        <span class="position-main">
          <b class="row-title">${item.ticker} · ${Number(item.shares).toFixed(0)} shares</b>
          <small class="row-meta">Average cost ${money.format(item.average_cost)} · latest price ${money.format(Number(item.price) || 0)}</small>
          <small class="row-meta thesis-summary"><span class="thesis-badge ${escapeHtml(thesis.label)}">${escapeHtml(thesis.label)}</span>${escapeHtml(thesis.summary || "")}</small>
          <details class="evidence-disclosure position-evidence">
            <summary>View position evidence</summary>
            <div class="evidence-content">
              <small class="row-meta">${escapeHtml(review.verdict || "unreviewed")} thesis review</small>
              ${renderDecisionDriver(item.decision_driver)}
              ${renderNewsSummary(item.news_summary)}
              ${memory?.summary ? `<small class="row-meta">Research memory: ${escapeHtml(memory.summary)}</small>` : ""}
              ${memory?.detail ? `<small class="row-meta">${escapeHtml(memory.detail)}</small>` : ""}
              ${journal.length ? `<div class="position-journal"><span>What changed since entry</span><ul>${journal.slice(0, 4).map(line => `<li>${escapeHtml(line)}</li>`).join("")}</ul></div>` : ""}
            </div>
          </details>
        </span>
        <span class="position-actions">
          <b class="row-title">${money.format(item.market_value || 0)}</b>
          <small class="row-meta ${changeClass(item.unrealized_gain_loss)}">${money.format(item.unrealized_gain_loss || 0)} open result</small>
          <button class="link-button" type="button" data-position-detail="${escapeHtml(item.ticker || "")}">Open holding</button>
        </span>
      </div>`;
  }).join("") || `<div class="empty">No open simulated positions.</div>`;
}

function renderNewsSummary(newsSummary) {
  if (!newsSummary || !newsSummary.label) return "";
  return `
    <small class="row-meta news-tone ${escapeHtml(newsSummary.label)}">
      <span class="news-tone-label">${escapeHtml(String(newsSummary.label).replaceAll("_", " "))}</span>
      ${escapeHtml(newsSummary.headline || "")}
    </small>
    ${newsSummary.detail ? `<small class="row-meta news-tone-detail">${escapeHtml(newsSummary.detail)}</small>` : ""}
    ${newsSummary.event_detail ? `<small class="row-meta news-tone-detail">${escapeHtml(newsSummary.event_detail)}</small>` : ""}
    ${newsSummary.example ? `<small class="row-meta news-tone-detail">Latest example: ${escapeHtml(newsSummary.example)}</small>` : ""}
  `;
}

function renderDecisionDriver(driver) {
  if (!driver || !driver.label) return "";
  const driverClass = driver.family === "projection"
    ? "tag driver-tag projection-driver-tag"
    : "tag driver-tag";
  return `
    <span class="${driverClass}">${escapeHtml(driver.label)}</span>
    ${driver.summary ? `<small class="row-meta decision-driver-meta">Driver: ${escapeHtml(driver.summary)}</small>` : ""}
  `;
}

function findPositionAccountability(ticker) {
  return (paperAccountabilityReport.tickers || []).find(item => item.ticker === ticker) || null;
}

function findPositionTradeHistory(ticker) {
  return (paperTradeHistory.tickers || []).find(item => item.ticker === ticker) || null;
}

function openPositionDetailDialog(ticker) {
  const position = paperPositions.find(item => item.ticker === ticker);
  if (!position) {
    showMessage("That paper holding is no longer available.", true);
    return;
  }
  const accountability = findPositionAccountability(ticker);
  const history = findPositionTradeHistory(ticker);
  const review = position.review || {};
  const thesis = position.thesis_status || {};
  const memory = position.research_memory || {};
  const journal = position.decision_journal || [];
  const adaptiveContext = Array.isArray(position.adaptive_context) ? position.adaptive_context : [];
  const outcomeSummary = position.outcome_summary || {};
  const trendSummary = position.trend_summary || {};
  const confirmationSummary = position.confirmation_summary || {};
  const projectionSummary = position.projection_summary || {};
  const decisionDriver = position.decision_driver || {};
  const transactions = accountability?.transactions || [];
  const latestTrade = transactions[transactions.length - 1] || null;
  const realized = Number(accountability?.realized_gain_loss || 0);
  const openBasis = Number(accountability?.open_basis || 0);
  const unrealized = Number(position.unrealized_gain_loss || 0);
  const totalResult = realized + unrealized;
  document.getElementById("position-detail-title").textContent = `${ticker} lifecycle detail`;
  document.getElementById("position-detail-summary").textContent =
    `${Number(position.shares || 0).toFixed(2)} open shares at ${money.format(Number(position.average_cost) || 0)} average cost · Open basis ${money.format(openBasis)} · Market value ${money.format(Number(position.market_value) || 0)}`;
  document.getElementById("position-detail-content").innerHTML = `
    <section class="basis-summary-grid position-detail-grid">
      <article class="basis-summary-card">
        <span class="summary-label">Current holding</span>
        <strong>${Number(position.shares || 0).toFixed(2)} shares</strong>
        <small>Latest price ${money.format(Number(position.price) || 0)}</small>
      </article>
      <article class="basis-summary-card">
        <span class="summary-label">Open basis</span>
        <strong>${money.format(openBasis)}</strong>
        <small>Weighted average cost ${money.format(Number(position.average_cost) || 0)}</small>
      </article>
      <article class="basis-summary-card">
        <span class="summary-label">Realized result</span>
        <strong class="${changeClass(realized)}">${money.format(realized)}</strong>
        <small>Completed simulated trims and exits</small>
      </article>
      <article class="basis-summary-card">
        <span class="summary-label">Total lifecycle result</span>
        <strong class="${changeClass(totalResult)}">${money.format(totalResult)}</strong>
        <small>Realized plus current unrealized result</small>
      </article>
    </section>
    <section class="position-detail-section">
      <div class="history-ticker-head">
        <div>
          <span class="role-chip">${escapeHtml(ticker)}</span>
          <strong>${escapeHtml(thesis.summary || "Atlas is waiting for the next thesis update.")}</strong>
          ${renderDecisionDriver(decisionDriver)}
        </div>
        <small class="row-meta">${escapeHtml(review.verdict || "unreviewed")} thesis · ${latestTrade ? `Latest trade ${new Date(latestTrade.timestamp).toLocaleString()}` : "No executed trades yet"}</small>
      </div>
      ${memory.summary || memory.detail ? `
        <div class="why-now compact memory">
          <span>Atlas memory</span>
          <ul>
            ${memory.summary ? `<li>${escapeHtml(memory.summary)}</li>` : ""}
            ${memory.detail ? `<li>${escapeHtml(memory.detail)}</li>` : ""}
          </ul>
        </div>
      ` : ""}
      ${journal.length ? `
        <div class="position-journal">
          <span>What changed since entry</span>
          <ul>${journal.map(line => `<li>${escapeHtml(line)}</li>`).join("")}</ul>
        </div>
      ` : ""}
      ${outcomeSummary.headline || outcomeSummary.detail ? `
        <div class="why-now compact">
          <span>Outcome framing</span>
          <ul>
            ${outcomeSummary.headline ? `<li>${escapeHtml(outcomeSummary.headline)}</li>` : ""}
            ${outcomeSummary.detail ? `<li>${escapeHtml(outcomeSummary.detail)}</li>` : ""}
          </ul>
        </div>
      ` : ""}
      ${projectionSummary.headline || projectionSummary.detail || (Array.isArray(projectionSummary.watchpoints) && projectionSummary.watchpoints.length) ? `
        <div class="why-now compact">
          <span>Projection watch</span>
          <ul>
            ${projectionSummary.headline ? `<li>${escapeHtml(projectionSummary.headline)}</li>` : ""}
            ${projectionSummary.detail ? `<li>${escapeHtml(projectionSummary.detail)}</li>` : ""}
            ${Array.isArray(projectionSummary.watchpoints) ? projectionSummary.watchpoints.map(line => `<li>${escapeHtml(line)}</li>`).join("") : ""}
          </ul>
        </div>
      ` : ""}
      ${adaptiveContext.length ? `
        <div class="why-now compact memory">
          <span>Adaptive context</span>
          <ul>${adaptiveContext.map(line => `<li>${escapeHtml(line)}</li>`).join("")}</ul>
        </div>
      ` : ""}
    </section>
    ${Array.isArray(trendSummary.stats) && trendSummary.stats.length ? `
      <section class="position-detail-section">
        <div class="history-ticker-head">
          <div>
            <span class="access-label">Trend diagnostics</span>
            <strong>${escapeHtml(trendSummary.headline || "Atlas trend diagnostics")}</strong>
          </div>
          <small class="row-meta">${escapeHtml(String(trendSummary.trend_regime || "unknown").replaceAll("_", " "))} regime Â· ${escapeHtml(String(trendSummary.trend_state || "unknown").replaceAll("_", " "))} state</small>
        </div>
        <div class="basis-summary-grid trend-summary-grid">
          ${trendSummary.stats.map(item => `
            <article class="basis-summary-card">
              <span class="summary-label">${escapeHtml(item.label || "Trend")}</span>
              <strong>${escapeHtml(item.value || "--")}</strong>
              <small>${escapeHtml(item.detail || "")}</small>
            </article>
          `).join("")}
        </div>
      </section>
    ` : ""}
    ${Array.isArray(confirmationSummary.stats) && confirmationSummary.stats.length ? `
      <section class="position-detail-section">
        <div class="history-ticker-head">
          <div>
            <span class="access-label">Confirmation check</span>
            <strong>${escapeHtml(confirmationSummary.headline || "Atlas confirmation check")}</strong>
          </div>
          <small class="row-meta">${escapeHtml(confirmationSummary.sector || "Sector")} sector ${confirmationSummary.strongest_benchmark ? `· strongest benchmark ${escapeHtml(confirmationSummary.strongest_benchmark)}` : ""}</small>
        </div>
        <div class="basis-summary-grid trend-summary-grid">
          ${confirmationSummary.stats.map(item => `
            <article class="basis-summary-card">
              <span class="summary-label">${escapeHtml(item.label || "Confirmation")}</span>
              <strong>${escapeHtml(item.value || "--")}</strong>
              <small>${escapeHtml(item.detail || "")}</small>
            </article>
          `).join("")}
        </div>
      </section>
    ` : ""}
    <section class="position-detail-section">
      <div class="history-ticker-head">
        <div>
          <span class="access-label">Execution timeline</span>
          <strong>${(history?.trade_count || transactions.length || 0).toFixed(0)} recorded trade${(history?.trade_count || transactions.length || 0) === 1 ? "" : "s"}</strong>
        </div>
        <small class="row-meta">Buys ${Number(accountability?.buy_shares || 0).toFixed(2)} · Sells ${Number(accountability?.sell_shares || 0).toFixed(2)} · Open ${Number(accountability?.open_shares || position.shares || 0).toFixed(2)}</small>
      </div>
      <div class="basis-table-wrap">
        <table class="basis-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Action</th>
              <th>Driver</th>
              <th>News event</th>
              <th>Shares</th>
              <th>Fill</th>
              <th>Basis</th>
              <th>Proceeds</th>
              <th>Realized</th>
              <th>Remaining</th>
            </tr>
          </thead>
          <tbody>
            ${transactions.length ? transactions.map(item => `
              <tr>
                <td>${escapeHtml(new Date(item.timestamp).toLocaleString())}</td>
                <td>${escapeHtml(String(item.action_label || item.side || "trade").replaceAll("_", " "))}</td>
                <td>${escapeHtml(item.decision_driver?.label || "--")}</td>
                <td>${escapeHtml(item.news_event_summary || "--")}</td>
                <td>${Number(item.shares || 0).toFixed(2)}</td>
                <td>${money.format(Number(item.fill_price) || 0)}</td>
                <td>${money.format(Number(item.basis_amount) || 0)}</td>
                <td>${item.proceeds !== null && item.proceeds !== undefined ? money.format(Number(item.proceeds) || 0) : "--"}</td>
                <td class="${changeClass(Number(item.realized_gain_loss) || 0)}">${item.side === "sell" ? money.format(Number(item.realized_gain_loss) || 0) : "--"}</td>
                <td>${Number(item.position_shares_after || 0).toFixed(2)} sh</td>
              </tr>
            `).join("") : `<tr><td colspan="10">No executed simulated trades are available for this holding yet.</td></tr>`}
          </tbody>
        </table>
      </div>
    </section>
    ${history?.rows?.length ? `
      <section class="position-detail-section">
        <div class="history-ticker-head">
          <div>
            <span class="access-label">Execution notes</span>
            <strong>Why Atlas acted</strong>
          </div>
          <small class="row-meta">Grouped from the paper trade history journal</small>
        </div>
        <div class="history-ticker-rows">
          ${history.rows.map(item => `
            <article class="history-row ${escapeHtml(item.side || "buy")}">
              <div>
                <span class="tag ${item.side === "sell" ? "exit-tag" : "buy-tag"}">${escapeHtml(String(item.action_label || item.side || "trade").replaceAll("_", " "))}</span>
                <b class="row-title">${new Date(item.timestamp).toLocaleString()} · ${Number(item.shares || 0).toFixed(2)} shares · ${money.format(Number(item.fill_price) || 0)}</b>
                <p>${escapeHtml(item.summary || "Atlas recorded a simulated trade.")}</p>
                <small class="row-meta">Thesis: ${escapeHtml(item.thesis || "No thesis supplied.")}</small>
                ${item.side === "sell" ? `<small class="row-meta ${changeClass(item.realized_gain_loss)}">Realized result ${money.format(Number(item.realized_gain_loss) || 0)}</small>` : ""}
              </div>
            </article>
          `).join("")}
        </div>
      </section>
    ` : ""}
  `;
  document.getElementById("position-detail-dialog").showModal();
}

function closePositionDetailDialog() {
  const dialog = document.getElementById("position-detail-dialog");
  if (dialog.open) dialog.close();
}

function renderPaperFeedback(rows) {
  document.getElementById("paper-feedback").innerHTML = rows.map(item => {
    const verdict = String(item.verdict || "not_enough_time");
    const action = String(item.action_label || (item.side === "sell" ? "sell" : "purchase"));
    const sideContext = item.side === "sell"
      ? `Post-sell move ${signed(item.security_return_pct)}`
      : `Return ${signed(item.security_return_pct)}`;
    const horizons = Array.isArray(item.horizon_outcomes) ? item.horizon_outcomes.filter(row => row.available) : [];
    const benchmarkText = ["SPY", "QQQ"].map(ticker => {
      const value = item.benchmark_returns_pct?.[ticker];
      return `${benchmarkLabel(ticker)} ${signed(value)}`;
    }).join(" · ");
    return `
      <article class="feedback-row ${escapeHtml(verdict)}">
        <div>
          <span class="tag verdict-tag">${escapeHtml(verdict).replaceAll("_", " ")}</span>
          <b class="row-title">${item.side === "sell" ? `${escapeHtml(item.ticker)} simulated ${escapeHtml(String(item.action_label || "sell"))}` : `${escapeHtml(item.ticker)} simulated buy`}</b>
          <small class="row-meta">Fill ${money.format(Number(item.fill_price) || 0)}${item.latest_price === null || item.latest_price === undefined ? "" : ` · latest ${money.format(Number(item.latest_price) || 0)}`}</small>
          <p>${escapeHtml(item.summary || "Atlas is waiting for enough evidence to judge this idea.")}</p>
          ${renderDecisionDriver(item.decision_driver)}
          <small class="row-meta">${sideContext} · ${benchmarkText} · ${Number(item.snapshots || 0).toFixed(0)} snapshots</small>
          ${horizons.length ? `<small class="row-meta">Persistence: ${horizons.map(row => `${escapeHtml(row.label)} ${escapeHtml(String(row.verdict || "unknown"))}`).join(" Â· ")}</small>` : ""}
          <small class="row-meta">Thesis: ${escapeHtml(item.thesis || "No thesis supplied.")}</small>
        </div>
      </article>`;
  }).join("") || `<div class="empty">No executed paper recommendations have enough tracking data yet.</div>`;
}

function renderPaperFeedbackSummary(summary) {
  const verdicts = summary.verdict_counts || {};
  const judged = Number(summary.judged || 0);
  const total = Number(summary.total || 0);
  const buyJudged = Number(summary.judged_side_counts?.buy || 0);
  const sellJudged = Number(summary.judged_side_counts?.sell || 0);
  const buyWorking = Number(summary.working_side_counts?.buy || 0);
  const sellWorking = Number(summary.working_side_counts?.sell || 0);
  const buyRate = buyJudged ? `${((buyWorking / buyJudged) * 100).toFixed(0)}%` : "--";
  const sellRate = sellJudged ? `${((sellWorking / sellJudged) * 100).toFixed(0)}%` : "--";
  const driverLearning = Array.isArray(summary.decision_driver_learning) ? summary.decision_driver_learning : [];
  const sellTriggerLearning = Array.isArray(summary.sell_trigger_learning) ? summary.sell_trigger_learning : [];
  const horizonLearning = Array.isArray(summary.horizon_learning) ? summary.horizon_learning : [];
  const entryProfile = summary.entry_strategy_profile || {};
  const projectionProfile = summary.projection_threshold_profile || {};
  const tradePressureProfile = summary.trade_pressure_profile || {};
  const benchmarkPreferenceProfile = summary.benchmark_preference_profile || {};
  const benchmarkScorecard = summary.benchmark_scorecard || {};
  const sectorLearningBridge = summary.sector_learning_bridge || {};
  const sectorGateAudit = summary.sector_gate_audit || {};
  const sectorGateOutcomes = summary.sector_gate_outcomes || {};
  const benchmarkScorecards = Array.isArray(benchmarkScorecard.scorecards) ? benchmarkScorecard.scorecards : [];
  const sectorLearningSectors = Array.isArray(sectorLearningBridge.sectors) ? sectorLearningBridge.sectors : [];
  const sectorGateExamples = Array.isArray(sectorGateAudit.candidate_examples) ? sectorGateAudit.candidate_examples : [];
  const sectorGateCandidateCounts = sectorGateAudit.candidate_counts || {};
  const sectorGateAcceptedCounts = sectorGateAudit.accepted_decision_counts || {};
  const sectorGateScorecards = Array.isArray(sectorGateOutcomes.scorecards) ? sectorGateOutcomes.scorecards : [];
  const entryAdjustments = Array.isArray(entryProfile.adjustments) ? entryProfile.adjustments : [];
  const projectionAdjustments = Array.isArray(projectionProfile.adjustments) ? projectionProfile.adjustments : [];
  const tradePressureAdjustments = Array.isArray(tradePressureProfile.adjustments) ? tradePressureProfile.adjustments : [];
  const benchmarkPreferenceAdjustments = Array.isArray(benchmarkPreferenceProfile.adjustments) ? benchmarkPreferenceProfile.adjustments : [];
  const takeaways = Array.isArray(summary.takeaways) ? summary.takeaways : [];
  document.getElementById("paper-feedback-summary").innerHTML = `
    <div class="feedback-summary-grid">
      <div class="feedback-summary-card spotlight">
        <span class="summary-label">Atlas learning readout</span>
        <strong>${escapeHtml(summary.headline || "Atlas is collecting paper-trade evidence.")}</strong>
        <small>${judged} judged of ${total} executed simulated trade${total === 1 ? "" : "s"}</small>
      </div>
      <div class="feedback-summary-card working">
        <span class="summary-label">Working</span>
        <strong>${Number(verdicts.working || 0)}</strong>
        <small>Ideas ahead of the current learning bar</small>
      </div>
      <div class="feedback-summary-card mixed">
        <span class="summary-label">Mixed</span>
        <strong>${Number(verdicts.mixed || 0)}</strong>
        <small>Partly confirmed, still nuanced</small>
      </div>
      <div class="feedback-summary-card lagging">
        <span class="summary-label">Lagging</span>
        <strong>${Number(verdicts.lagging || 0)}</strong>
        <small>Ideas trailing the current bar</small>
      </div>
    </div>
    <div class="feedback-takeaways">
      <div class="feedback-takeaway-card">
        <span class="access-label">Buy calibration</span>
        <strong>${buyRate}</strong>
        <small>${buyWorking} of ${buyJudged} judged simulated buys are working</small>
      </div>
      <div class="feedback-takeaway-card">
        <span class="access-label">Sell calibration</span>
        <strong>${sellRate}</strong>
        <small>${sellWorking} of ${sellJudged} judged trims/exits are helping</small>
      </div>
    </div>
    ${sellTriggerLearning.length ? `
      <div class="feedback-driver-learning">
        ${sellTriggerLearning.map(item => `
          <div class="feedback-driver-card">
            <span class="thesis-badge ready">Sell trigger</span>
            <strong>${escapeHtml(item.label || "Sell trigger")}</strong>
            <small>${item.working} working, ${item.mixed} mixed, ${item.lagging} lagging across ${item.judged} judged trim${item.judged === 1 ? "" : "s"} or exits.</small>
            <p>${item.working_rate_pct === null || item.working_rate_pct === undefined ? "--" : `${Number(item.working_rate_pct).toFixed(0)}%`} of judged trims/exits using this trigger are currently helping.</p>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${driverLearning.length ? `
      <div class="feedback-driver-learning">
        ${driverLearning.map(item => `
          <div class="feedback-driver-card">
            ${renderDecisionDriver({ family: "projection", label: item.label, summary: `${item.working} working, ${item.mixed} mixed, ${item.lagging} lagging across ${item.judged} judged trade${item.judged === 1 ? "" : "s"}.` })}
            <strong>${item.working_rate_pct === null || item.working_rate_pct === undefined ? "--" : `${Number(item.working_rate_pct).toFixed(0)}%`}</strong>
            <small>${item.working} of ${item.judged} judged trades currently look working</small>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${horizonLearning.length ? `
      <div class="feedback-driver-learning">
        ${horizonLearning.map(item => `
          <div class="feedback-driver-card">
            <span class="thesis-badge ready">Persistence</span>
            <strong>${escapeHtml(item.label || "Snapshot persistence")}</strong>
            <small>${item.working} working, ${item.mixed} mixed, ${item.lagging} lagging across ${item.judged} judged trade${item.judged === 1 ? "" : "s"}.</small>
            <p>${item.working_rate_pct === null || item.working_rate_pct === undefined ? "--" : `${Number(item.working_rate_pct).toFixed(0)}%`} of judged trades are still working at this checkpoint.</p>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${projectionProfile.enabled ? `
      <div class="feedback-takeaways">
        <div class="feedback-takeaway-card">
          <span class="access-label">Adaptive projection tuning</span>
          <strong>${projectionProfile.active ? "Active" : "Watching"}</strong>
          <small>${escapeHtml(projectionProfile.headline || "Atlas is monitoring projection outcomes.")}</small>
        </div>
        <div class="feedback-takeaway-card">
          <span class="access-label">Judged inputs</span>
          <strong>${Number(projectionProfile.judged_trades || 0)}</strong>
          <small>judged projection-linked paper trades used for retuning</small>
        </div>
      </div>
    ` : ""}
    ${entryProfile.enabled ? `
      <div class="feedback-takeaways">
        <div class="feedback-takeaway-card">
          <span class="access-label">Adaptive entry pacing</span>
          <strong>${entryProfile.active ? "Active" : "Watching"}</strong>
          <small>${escapeHtml(entryProfile.headline || "Atlas is monitoring how aggressively it should rotate capital into new paper ideas.")}</small>
        </div>
        <div class="feedback-takeaway-card">
          <span class="access-label">Benchmark rotation read</span>
          <strong>${escapeHtml(String(entryProfile.benchmark_rotation_stats?.benchmark || "AUTO").toUpperCase())}</strong>
          <small>${Number(entryProfile.benchmark_rotation_stats?.judged || 0)} judged buy comparisons used for sector and capital pacing</small>
        </div>
      </div>
    ` : ""}
    ${sectorLearningBridge.enabled ? `
      <div class="feedback-driver-learning">
        <div class="feedback-driver-card">
          <span class="thesis-badge ready">Sector learning bridge</span>
          <strong>${sectorLearningBridge.active ? "Active" : "Watching"}</strong>
          <small>${escapeHtml(sectorLearningBridge.headline || "Atlas is tracking whether sector-level paper buys are earning a small strategy tilt.")}</small>
          <p>Sector learning gate: checkpoint ${escapeHtml(sectorLearningBridge.checkpoint || "3-snapshot persistence")} · minimum ${Number(sectorLearningBridge.minimum_judged_buys || 2)} judged buys per sector.</p>
        </div>
        ${sectorLearningSectors.slice(0, 5).map(item => `
          <div class="feedback-driver-card">
            <span class="thesis-badge ${escapeHtml(item.posture || "watch")}">${escapeHtml(item.posture || "watch")}</span>
            <strong>${escapeHtml(item.sector || "Unclassified")}</strong>
            <small>${Number(item.working || 0)} working, ${Number(item.mixed || 0)} mixed, ${Number(item.lagging || 0)} lagging across ${Number(item.judged || 0)} judged buy${Number(item.judged || 0) === 1 ? "" : "s"}.</small>
            <p>${escapeHtml(item.summary || "Atlas is collecting sector-level paper learning evidence.")} Strategy tilt ${Number(item.adjustment || 0) >= 0 ? "+" : ""}${Number(item.adjustment || 0).toFixed(1)}.</p>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${sectorGateAudit.enabled ? `
      <div class="feedback-driver-learning">
        <div class="feedback-driver-card">
          <span class="thesis-badge ready">Sector gate audit</span>
          <strong>${sectorGateAudit.active ? "Active" : "Watching"}</strong>
          <small>${escapeHtml(sectorGateAudit.headline || "Atlas is measuring how sector-learning gates affect simulated entries.")}</small>
          <p>${Number(sectorGateCandidateCounts.active || 0)} active gated candidate${Number(sectorGateCandidateCounts.active || 0) === 1 ? "" : "s"} today: ${Number(sectorGateCandidateCounts.cleared || 0)} cleared, ${Number(sectorGateCandidateCounts.tightened || 0)} tightened, ${Number(sectorGateCandidateCounts.boost || 0)} boosted.</p>
          <p>${Number(sectorGateAcceptedCounts.with_gate || 0)} accepted simulated buy${Number(sectorGateAcceptedCounts.with_gate || 0) === 1 ? "" : "s"} include a sector-gate rationale: ${Number(sectorGateAcceptedCounts.cleared || 0)} cleared, ${Number(sectorGateAcceptedCounts.tightened || 0)} tightened, ${Number(sectorGateAcceptedCounts.boost || 0)} boosted.</p>
        </div>
        ${sectorGateExamples.slice(0, 4).map(item => `
          <div class="feedback-driver-card">
            <span class="thesis-badge ${escapeHtml(item.status || "watch")}">${escapeHtml(item.status || "watch")}</span>
            <strong>${escapeHtml(item.ticker || "--")} ${escapeHtml(item.sector || "Unclassified")}</strong>
            <small>${Number(item.passed_checks || 0)} of ${Number(item.total_checks || 0)} stronger confirmation checks passed.</small>
            <p>${escapeHtml(item.summary || "Atlas is measuring this sector-learning gate.")} ${item.buy_eligible ? "Currently eligible for simulated entry." : "Not eligible for simulated entry yet."}</p>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${sectorGateOutcomes.enabled ? `
      <div class="feedback-driver-learning">
        <div class="feedback-driver-card">
          <span class="thesis-badge ready">Sector gate outcomes</span>
          <strong>${sectorGateOutcomes.active ? "Judging" : "Waiting"}</strong>
          <small>${escapeHtml(sectorGateOutcomes.headline || "Atlas is measuring whether accepted sector-gate buys are beating the benchmark bar.")}</small>
          <p>${sectorGateOutcomes.leader ? `Current leader: ${escapeHtml(sectorGateOutcomes.leader.label || sectorGateOutcomes.leader.status || "sector gate")} at ${Number(sectorGateOutcomes.leader.working_rate_pct || 0).toFixed(0)}% working.` : "No accepted sector-gate buy has enough judged outcome evidence yet."}</p>
        </div>
        ${sectorGateScorecards.slice(0, 4).map(item => `
          <div class="feedback-driver-card">
            <span class="thesis-badge ${escapeHtml(item.status || "watch")}">${escapeHtml(item.status || "watch")}</span>
            <strong>${escapeHtml(item.label || "Sector gate")}</strong>
            <small>${Number(item.working || 0)} working, ${Number(item.mixed || 0)} mixed, ${Number(item.lagging || 0)} lagging across ${Number(item.judged || 0)} judged accepted buy${Number(item.judged || 0) === 1 ? "" : "s"}.</small>
            <p>${item.working_rate_pct === null || item.working_rate_pct === undefined ? "--" : `${Number(item.working_rate_pct).toFixed(0)}%`} working rate; average edge ${item.avg_edge_pct === null || item.avg_edge_pct === undefined ? "--" : `${Number(item.avg_edge_pct).toFixed(2)}%`} versus the stronger SPY/QQQ bar.</p>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${tradePressureProfile.enabled ? `
      <div class="feedback-takeaways">
        <div class="feedback-takeaway-card">
          <span class="access-label">Adaptive trade pressure</span>
          <strong>${tradePressureProfile.active ? "Active" : "Watching"}</strong>
          <small>${escapeHtml(tradePressureProfile.headline || "Atlas is monitoring how quickly it should turn the paper book.")}</small>
        </div>
        <div class="feedback-takeaway-card">
          <span class="access-label">Current daily cap</span>
          <strong>${escapeHtml(String(tradePressureProfile.policy_overrides?.maximum_daily_trades ?? tradePressureProfile.baseline?.maximum_daily_trades ?? "--"))}</strong>
          <small>simulated trades per day after current learning overrides</small>
        </div>
      </div>
    ` : ""}
    ${benchmarkPreferenceProfile.enabled ? `
      <div class="feedback-takeaways">
        <div class="feedback-takeaway-card">
          <span class="access-label">Adaptive benchmark trust</span>
          <strong>${benchmarkPreferenceProfile.active ? "Active" : "Watching"}</strong>
          <small>${escapeHtml(benchmarkPreferenceProfile.headline || "Atlas is monitoring which benchmark bar explains outcomes best.")}</small>
        </div>
        <div class="feedback-takeaway-card">
          <span class="access-label">Current benchmark bar</span>
          <strong>${escapeHtml(String(benchmarkPreferenceProfile.strategy_overrides?.strategy_preferred_benchmark || benchmarkPreferenceProfile.baseline?.strategy_preferred_benchmark || "auto").toUpperCase())}</strong>
          <small>${escapeHtml(String(benchmarkPreferenceProfile.strategy_overrides?.strategy_preferred_benchmark || benchmarkPreferenceProfile.baseline?.strategy_preferred_benchmark || "auto").toUpperCase() === "AUTO" ? "Atlas is still auto-picking the stronger daily benchmark." : "Atlas is using the learned benchmark as the stronger bar for borderline entries.")}</small>
        </div>
      </div>
    ` : ""}
    ${benchmarkScorecard.enabled ? `
      <div class="feedback-driver-learning">
        <div class="feedback-driver-card">
          <span class="thesis-badge ready">Benchmark scorecard</span>
          <strong>${escapeHtml(benchmarkScorecard.headline || "Atlas is tracking benchmark-specific paper outcomes.")}</strong>
          <small>${Number(benchmarkScorecard.judged || 0)} judged benchmark comparisons across simulated buys, trims, and exits.</small>
        </div>
        ${benchmarkScorecards.map(item => `
          <div class="feedback-driver-card">
            <span class="thesis-badge ready">${escapeHtml(item.benchmark || "Benchmark")}</span>
            <strong>${item.working_rate_pct === null || item.working_rate_pct === undefined ? "--" : `${Number(item.working_rate_pct).toFixed(0)}%`}</strong>
            <small>${escapeHtml(item.label || benchmarkLabel(item.benchmark || ""))}</small>
            <p>${Number(item.working || 0)} working, ${Number(item.mixed || 0)} mixed, ${Number(item.lagging || 0)} lagging. Avg decision edge ${signed(item.avg_decision_edge_pct)}.</p>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${projectionAdjustments.length ? `
      <div class="feedback-driver-learning">
        ${projectionAdjustments.map(item => `
          <div class="feedback-driver-card">
            <span class="thesis-badge ready">${escapeHtml(item.direction || "adjusted")}</span>
            <strong>${escapeHtml(item.label || "Projection tuning")}</strong>
            <small>${escapeHtml(String(item.from ?? "--"))} to ${escapeHtml(String(item.to ?? "--"))}</small>
            <p>${escapeHtml(item.reason || "Atlas adjusted this threshold from judged paper outcomes.")}</p>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${entryAdjustments.length ? `
      <div class="feedback-driver-learning">
        ${entryAdjustments.map(item => `
          <div class="feedback-driver-card">
            <span class="thesis-badge ready">${escapeHtml(item.direction || "adjusted")}</span>
            <strong>${escapeHtml(item.label || "Entry pacing")}</strong>
            <small>${escapeHtml(String(item.from ?? "--"))} to ${escapeHtml(String(item.to ?? "--"))}</small>
            <p>${escapeHtml(item.reason || "Atlas adjusted entry pacing from judged paper outcomes.")}</p>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${tradePressureAdjustments.length ? `
      <div class="feedback-driver-learning">
        ${tradePressureAdjustments.map(item => `
          <div class="feedback-driver-card">
            <span class="thesis-badge ready">${escapeHtml(item.direction || "adjusted")}</span>
            <strong>${escapeHtml(item.label || "Trade pressure")}</strong>
            <small>${escapeHtml(String(item.from ?? "--"))} to ${escapeHtml(String(item.to ?? "--"))}</small>
            <p>${escapeHtml(item.reason || "Atlas adjusted daily trade pressure from judged paper outcomes.")}</p>
          </div>
        `).join("")}
      </div>
    ` : ""}
    ${benchmarkPreferenceAdjustments.length ? `
      <div class="feedback-driver-learning">
        ${benchmarkPreferenceAdjustments.map(item => `
          <div class="feedback-driver-card">
            <span class="thesis-badge ready">Benchmark trust</span>
            <strong>${escapeHtml(item.label || "Benchmark trust")}</strong>
            <small>${escapeHtml(String(item.from ?? "--").toUpperCase())} to ${escapeHtml(String(item.to ?? "--").toUpperCase())}</small>
            <p>${escapeHtml(item.reason || "Atlas adjusted which benchmark bar it trusts from judged paper outcomes.")}</p>
          </div>
        `).join("")}
      </div>
    ` : ""}
    <div class="feedback-takeaway-list">
      ${(takeaways.length ? takeaways : ["Atlas needs more post-trade data before the learning summary becomes meaningful."]).map(item => `
        <div class="feedback-takeaway-row">
          <span class="thesis-badge ready">Learning</span>
          <small>${escapeHtml(item)}</small>
        </div>
      `).join("")}
    </div>
  `;
}

function renderCapitalRotationScoreboard(scoreboard) {
  const target = document.getElementById("capital-rotation-scoreboard");
  if (!target) return;
  const sectors = Array.isArray(scoreboard.sectors) ? scoreboard.sectors : [];
  const totals = scoreboard.totals || {};
  const rotationRead = scoreboard.benchmark_rotation_read || {};
  if (!scoreboard.available || !sectors.length) {
    target.innerHTML = `
      <div class="capital-rotation-empty">
        <span class="thesis-badge watch">Capital rotation scoreboard</span>
        <strong>${escapeHtml(scoreboard.headline || "Atlas is waiting for enough simulated sector activity to score capital rotation.")}</strong>
      </div>`;
    return;
  }
  target.innerHTML = `
    <div class="capital-rotation-header">
      <div>
        <span class="access-label">Capital rotation scoreboard</span>
        <strong>${escapeHtml(scoreboard.headline || "Atlas is watching where simulated capital is earning the right to expand.")}</strong>
        <small>Read-only sector accountability for simulated buys, sells, exposure, and benchmark-relative buy outcomes.</small>
      </div>
      <div class="capital-rotation-read">
        <span>Benchmark buy read</span>
        <b>${escapeHtml(String(rotationRead.benchmark || "AUTO").toUpperCase())}</b>
        <small>${Number(rotationRead.judged || 0)} judged comparisons</small>
      </div>
    </div>
    <div class="capital-rotation-totals">
      <div><span>Open value</span><strong>${money.format(Number(totals.open_market_value || 0))}</strong></div>
      <div><span>Net committed</span><strong>${money.format(Number(totals.net_notional || 0))}</strong></div>
      <div><span>Realized P/L</span><strong>${money.format(Number(totals.realized_gain_loss || 0))}</strong></div>
      <div><span>Unrealized P/L</span><strong>${money.format(Number(totals.unrealized_gain_loss || 0))}</strong></div>
      <div><span>Buy hit rate</span><strong>${totals.buy_working_rate_pct === null || totals.buy_working_rate_pct === undefined ? "--" : `${Number(totals.buy_working_rate_pct).toFixed(0)}%`}</strong></div>
    </div>
    <div class="capital-rotation-grid">
      ${sectors.map(row => `
        <article class="capital-rotation-card ${escapeHtml(row.posture || "watch")}">
          <div class="capital-rotation-card-head">
            <span class="thesis-badge ${escapeHtml(row.posture || "watch")}">${escapeHtml(String(row.posture || "watch"))}</span>
            <strong>${escapeHtml(row.sector || "Unclassified")}</strong>
          </div>
          <p>${escapeHtml(row.summary || "Atlas is collecting sector-level paper evidence.")}</p>
          <dl>
            <div><dt>Open exposure</dt><dd>${money.format(Number(row.open_market_value || 0))} · ${Number(row.open_weight_pct || 0).toFixed(1)}%</dd></div>
            <div><dt>Buys / sells</dt><dd>${money.format(Number(row.buy_notional || 0))} / ${money.format(Number(row.sell_notional || 0))}</dd></div>
            <div><dt>Net committed</dt><dd>${money.format(Number(row.net_notional || 0))}</dd></div>
            <div><dt>Realized / unrealized</dt><dd>${money.format(Number(row.realized_gain_loss || 0))} / ${money.format(Number(row.unrealized_gain_loss || 0))}</dd></div>
            <div><dt>Judged buys</dt><dd>${Number(row.working_buys || 0)} working of ${Number(row.judged_buys || 0)}</dd></div>
            <div><dt>Avg benchmark edge</dt><dd>${row.avg_benchmark_edge_pct === null || row.avg_benchmark_edge_pct === undefined ? "--" : signed(row.avg_benchmark_edge_pct)}</dd></div>
          </dl>
        </article>
      `).join("")}
    </div>`;
}

function renderValidationSummary(summary) {
  const scorecards = Array.isArray(summary.scorecards) ? summary.scorecards : [];
  const takeaways = Array.isArray(summary.takeaways) ? summary.takeaways : [];
  const readiness = summary.capital_readiness || {};
  const readinessCriteria = Array.isArray(readiness.criteria) ? readiness.criteria : [];
  const stateClass = escapeHtml(String(summary.status || "building"));
  const html = `
    <div class="feedback-summary-grid validation-grid">
      <div class="feedback-summary-card spotlight validation-spotlight ${stateClass}">
        <span class="summary-label">Stage 5 status</span>
        <strong>${escapeHtml(summary.status_label || "Evidence building")}</strong>
        <small>${escapeHtml(summary.headline || "Atlas is building paper-trading validation evidence.")}</small>
        <p>${escapeHtml(summary.detail || "Benchmark-relative paper evidence will appear here as Atlas accumulates snapshots and judged trade outcomes.")}</p>
      </div>
      ${readinessCriteria.length ? `
        <div class="feedback-summary-card spotlight capital-readiness ${readiness.ready_for_owner_review ? "ready" : "paper-only"}">
          <span class="summary-label">Real-capital discussion gate</span>
          <strong>${escapeHtml(readiness.status_label || "Paper only")}</strong>
          <small>${escapeHtml(readiness.headline || "Atlas must prove itself in simulation first.")}</small>
          <p>${escapeHtml(readiness.detail || "")}</p>
          <div class="capital-readiness-list">
            ${readinessCriteria.map(item => `
              <div class="capital-readiness-row ${item.passed ? "passed" : "open"}">
                <span>${item.passed ? "Pass" : "Open"}</span>
                <div>
                  <b>${escapeHtml(item.label || "Evidence gate")}</b>
                  <small>${escapeHtml(item.current || "N/A")} | target ${escapeHtml(item.target || "")}</small>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      ` : ""}
      ${scorecards.map(item => `
        <div class="feedback-summary-card">
          <span class="summary-label">${escapeHtml(item.label || "Metric")}</span>
          <strong>${escapeHtml(String(item.value ?? "--"))}</strong>
          <small>${escapeHtml(item.detail || "")}</small>
        </div>
      `).join("")}
    </div>
    <div class="feedback-takeaway-list">
      ${(takeaways.length ? takeaways : ["Atlas is still collecting the evidence needed to complete Stage 5 validation."]).map(item => `
        <div class="feedback-takeaway-row">
          <span class="thesis-badge ready">Stage 5</span>
          <small>${escapeHtml(item)}</small>
        </div>
      `).join("")}
    </div>
  `;
  ["overview-validation-summary", "paper-validation-summary"].forEach(id => {
    const target = document.getElementById(id);
    if (target) target.innerHTML = html;
  });
}

function renderRoadmap(data) {
  const summary = data.paper?.validation_summary || {};
  const pipeline = summary.evidence_pipeline || {};
  const readiness = summary.capital_readiness || {};
  const passed = Number(readiness.passed || 0);
  const total = Number(readiness.total || 0);
  const progress = Math.max(0, Math.min(100, Number(readiness.progress_pct) || 0));
  const values = {
    "roadmap-snapshots": Number(pipeline.snapshot_count || summary.snapshots || 0),
    "roadmap-judged": Number(pipeline.judged_decisions || summary.judged_trades || 0),
    "roadmap-completed": Number(pipeline.completed_positions || summary.realized_exits || 0),
    "roadmap-gates": total ? `${passed}/${total}` : "--",
  };
  Object.entries(values).forEach(([id, value]) => {
    const node = document.getElementById(id);
    if (node) node.textContent = String(value);
  });
  const label = document.getElementById("roadmap-stage5-label");
  if (label) {
    label.textContent = total
      ? `${progress.toFixed(1)}% · ${passed} of ${total} gates passing`
      : "Building evidence";
  }
  const bar = document.getElementById("roadmap-stage5-progress");
  if (bar) bar.style.width = `${progress}%`;
}

function renderPaperActivity(rows) {
  document.getElementById("paper-activity").innerHTML = rows.map(item => {
    const action = String(item.action_label || item.side || "activity");
    const rationale = item.rationale || [];
    const decisionContext = item.decision_context || [];
    const whyHeading = action === "trim" ? "Why trim" : action === "exit" ? "Why exit" : "Why buy";
    return `
      <article class="activity-row ${escapeHtml(item.side || "buy")}">
        <div>
          <span class="tag ${item.side === "sell" ? "exit-tag" : "buy-tag"}">${escapeHtml(action).replaceAll("_", " ")}</span>
          <b class="row-title">${escapeHtml(item.title || "Atlas activity")}</b>
          <small class="row-meta">${new Date(item.timestamp).toLocaleString()} · ${Number(item.shares || 0).toFixed(2)} shares · ${money.format(Number(item.fill_price) || 0)}</small>
          <p>${escapeHtml(item.summary || "Atlas recorded a simulated trade.")}</p>
          ${item.side === "sell" ? `<small class="row-meta ${changeClass(item.realized_gain_loss)}">Realized result ${money.format(Number(item.realized_gain_loss) || 0)}</small>` : ""}
          <details class="evidence-disclosure activity-evidence">
            <summary>Why Atlas acted</summary>
            <div class="evidence-content">
              ${renderDecisionDriver(item.decision_driver)}
              <small class="row-meta">Thesis: ${escapeHtml(item.thesis || "No thesis supplied.")}</small>
              ${rationale.length ? `<div class="why-now compact"><span>${whyHeading}</span><ul>${rationale.slice(0, 3).map(reason => `<li>${escapeHtml(reason)}</li>`).join("")}</ul></div>` : ""}
              ${decisionContext.length ? `<div class="why-now compact memory"><span>Atlas context</span><ul>${decisionContext.slice(0, 4).map(reason => `<li>${escapeHtml(reason)}</li>`).join("")}</ul></div>` : ""}
            </div>
          </details>
        </div>
      </article>`;
  }).join("") || `<div class="empty">No simulated buys or sells have been recorded yet.</div>`;
}

function renderTradeHistory(history) {
  paperTradeHistory = history || { total_trades: 0, ticker_count: 0, tickers: [] };
  const button = document.getElementById("open-trade-history");
  button.disabled = !paperTradeHistory.total_trades;
  button.textContent = paperTradeHistory.total_trades
    ? `View trade history (${paperTradeHistory.ticker_count} ticker${paperTradeHistory.ticker_count === 1 ? "" : "s"})`
    : "View trade history";
  document.getElementById("trade-history-summary").textContent = paperTradeHistory.total_trades
    ? `${paperTradeHistory.total_trades} simulated trade${paperTradeHistory.total_trades === 1 ? "" : "s"} across ${paperTradeHistory.ticker_count} ticker${paperTradeHistory.ticker_count === 1 ? "" : "s"}.`
    : "No simulated trade history is available yet.";
  document.getElementById("trade-history-content").innerHTML = paperTradeHistory.tickers.length
    ? paperTradeHistory.tickers.map(group => `
      <section class="history-ticker">
        <div class="history-ticker-head">
          <div>
            <span class="role-chip">${escapeHtml(group.ticker)}</span>
            <strong>${Number(group.trade_count || 0).toFixed(0)} trade${Number(group.trade_count || 0) === 1 ? "" : "s"}</strong>
          </div>
          <small class="row-meta">${Number(group.buy_count || 0).toFixed(0)} buy · ${Number(group.sell_count || 0).toFixed(0)} sell</small>
        </div>
        <div class="history-ticker-rows">
          ${group.rows.map(item => `
            <article class="history-row ${escapeHtml(item.side || "buy")}">
              <div>
                <span class="tag ${item.side === "sell" ? "exit-tag" : "buy-tag"}">${escapeHtml(String(item.action_label || item.side || "trade").replaceAll("_", " "))}</span>
                <b class="row-title">${new Date(item.timestamp).toLocaleString()} · ${Number(item.shares || 0).toFixed(2)} shares · ${money.format(Number(item.fill_price) || 0)}</b>
                <p>${escapeHtml(item.summary || "Atlas recorded a simulated trade.")}</p>
                ${renderDecisionDriver(item.decision_driver)}
                <small class="row-meta">Thesis: ${escapeHtml(item.thesis || "No thesis supplied.")}</small>
                ${item.side === "sell" ? `<small class="row-meta ${changeClass(item.realized_gain_loss)}">Realized result ${money.format(Number(item.realized_gain_loss) || 0)}</small>` : ""}
                ${Array.isArray(item.decision_context) && item.decision_context.length ? `<div class="why-now compact memory"><span>Atlas context</span><ul>${item.decision_context.slice(0, 3).map(line => `<li>${escapeHtml(line)}</li>`).join("")}</ul></div>` : ""}
              </div>
            </article>
          `).join("")}
        </div>
      </section>
    `).join("")
    : `<div class="empty">No simulated trade history is available yet.</div>`;
}

function renderAccountabilityReport(report) {
  paperAccountabilityReport = report || { summary: {}, tickers: [] };
  const summary = paperAccountabilityReport.summary || {};
  const tickers = paperAccountabilityReport.tickers || [];
  const transactionCount = Number(summary.transactions || 0);
  const openButton = document.getElementById("open-basis-report");
  const exportButton = document.getElementById("export-basis-report");
  openButton.disabled = !transactionCount;
  exportButton.disabled = !transactionCount;
  openButton.textContent = transactionCount
    ? `Open basis report (${Number(summary.tickers || 0)} ticker${Number(summary.tickers || 0) === 1 ? "" : "s"})`
    : "Open basis report";
  document.getElementById("basis-report-summary").textContent = transactionCount
    ? `${transactionCount} executed trade${transactionCount === 1 ? "" : "s"} · ${Number(summary.open_positions || 0)} open position${Number(summary.open_positions || 0) === 1 ? "" : "s"} · Open basis ${money.format(Number(summary.total_open_basis) || 0)}`
    : "No executed simulated trades are available for basis reporting yet.";
  document.getElementById("basis-report-content").innerHTML = tickers.length
    ? `
      <section class="basis-summary-grid">
        <article class="basis-summary-card">
          <span class="summary-label">Accounting method</span>
          <strong>${escapeHtml(String(report.accounting_method || "weighted_average_cost").replaceAll("_", " "))}</strong>
          <small>Simulated paper-account basis method</small>
        </article>
        <article class="basis-summary-card">
          <span class="summary-label">Total buy basis</span>
          <strong>${money.format(Number(summary.total_buy_basis) || 0)}</strong>
          <small>Gross basis committed across simulated purchases</small>
        </article>
        <article class="basis-summary-card">
          <span class="summary-label">Sale proceeds</span>
          <strong>${money.format(Number(summary.total_sale_proceeds) || 0)}</strong>
          <small>Gross proceeds across simulated trims and exits</small>
        </article>
        <article class="basis-summary-card">
          <span class="summary-label">Realized result</span>
          <strong class="${changeClass(Number(summary.total_realized_gain_loss) || 0)}">${money.format(Number(summary.total_realized_gain_loss) || 0)}</strong>
          <small>Aggregate realized gain or loss from completed sells</small>
        </article>
      </section>
      ${tickers.map(group => `
        <section class="history-ticker basis-ticker">
          <div class="history-ticker-head">
            <div>
              <span class="role-chip">${escapeHtml(group.ticker)}</span>
              <strong>Open shares ${Number(group.open_shares || 0).toFixed(2)} · Open basis ${money.format(Number(group.open_basis) || 0)}</strong>
            </div>
            <small class="row-meta">Average cost ${group.average_cost !== null && group.average_cost !== undefined ? money.format(Number(group.average_cost) || 0) : "--"} · Realized ${money.format(Number(group.realized_gain_loss) || 0)}</small>
          </div>
          <div class="basis-table-wrap">
            <table class="basis-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Action</th>
                  <th>Driver</th>
                  <th>News event</th>
                  <th>Adaptive regime</th>
                  <th>Shares</th>
                  <th>Fill</th>
                  <th>Basis/Share</th>
                  <th>Basis</th>
                  <th>Proceeds</th>
                  <th>Realized</th>
                  <th>Remaining</th>
                </tr>
              </thead>
              <tbody>
                ${group.transactions.map(item => `
                  <tr>
                    <td>${escapeHtml(new Date(item.timestamp).toLocaleString())}</td>
                    <td>${escapeHtml(String(item.action_label || item.side || "trade").replaceAll("_", " "))}</td>
                    <td>${escapeHtml(item.decision_driver?.label || "--")}</td>
                    <td>${escapeHtml(item.news_event_summary || "--")}</td>
                    <td>${escapeHtml(item.adaptive_regime || "--")}</td>
                    <td>${Number(item.shares || 0).toFixed(2)}</td>
                    <td>${money.format(Number(item.fill_price) || 0)}</td>
                    <td>${item.basis_per_share !== null && item.basis_per_share !== undefined ? money.format(Number(item.basis_per_share) || 0) : "--"}</td>
                    <td>${money.format(Number(item.basis_amount) || 0)}</td>
                    <td>${item.proceeds !== null && item.proceeds !== undefined ? money.format(Number(item.proceeds) || 0) : "--"}</td>
                    <td class="${changeClass(Number(item.realized_gain_loss) || 0)}">${item.side === "sell" ? money.format(Number(item.realized_gain_loss) || 0) : "--"}</td>
                    <td>${Number(item.position_shares_after || 0).toFixed(2)} sh</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </section>
      `).join("")}
    `
    : `<div class="empty">No executed simulated trades are available for basis reporting yet.</div>`;
}

function openTradeHistoryDialog() {
  document.getElementById("trade-history-dialog").showModal();
}

function closeTradeHistoryDialog() {
  const dialog = document.getElementById("trade-history-dialog");
  if (dialog.open) dialog.close();
}

function openBasisReportDialog() {
  document.getElementById("basis-report-dialog").showModal();
}

function closeBasisReportDialog() {
  const dialog = document.getElementById("basis-report-dialog");
  if (dialog.open) dialog.close();
}

function exportBasisReportCsv() {
  const rows = [["Ticker", "Timestamp", "Action", "Driver", "Driver Detail", "News Event", "Adaptive Regime", "Shares", "Fill Price", "Basis Per Share", "Basis Amount", "Proceeds", "Realized Gain Loss", "Position Shares After", "Open Shares", "Average Cost", "Open Basis"]];
  (paperAccountabilityReport.tickers || []).forEach(group => {
    (group.transactions || []).forEach(item => {
      rows.push([
        group.ticker || "",
        item.timestamp || "",
        item.action_label || item.side || "",
        item.decision_driver?.label || "",
        item.decision_driver?.summary || "",
        item.news_event_summary || "",
        item.adaptive_regime || "",
        Number(item.shares || 0).toFixed(2),
        Number(item.fill_price || 0).toFixed(4),
        item.basis_per_share === null || item.basis_per_share === undefined ? "" : Number(item.basis_per_share).toFixed(4),
        Number(item.basis_amount || 0).toFixed(2),
        item.proceeds === null || item.proceeds === undefined ? "" : Number(item.proceeds).toFixed(2),
        item.side === "sell" ? Number(item.realized_gain_loss || 0).toFixed(2) : "",
        Number(item.position_shares_after || 0).toFixed(2),
        Number(group.open_shares || 0).toFixed(2),
        group.average_cost === null || group.average_cost === undefined ? "" : Number(group.average_cost).toFixed(4),
        Number(group.open_basis || 0).toFixed(2),
      ]);
    });
  });
  const csv = rows.map(columns => columns.map(value => `"${String(value ?? "").replaceAll('"', '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "atlas-paper-basis-report.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function renderPaperOperatingMode(mode) {
  const current = mode.current || {};
  const modes = mode.modes || [];
  const settings = mode.strategy_settings || [];
  document.getElementById("paper-operating-mode").innerHTML = `
    <div class="mode-current">
      <span class="access-label">Current mode</span>
      <strong>${escapeHtml(current.label || "Recommendation mode")}</strong>
      <p>${escapeHtml(current.description || "Atlas is currently operating as a recommendation engine.")}</p>
      <small>${escapeHtml(mode.boundary || "Real-money trading remains disabled.")}</small>
    </div>
    <div class="mode-options strategy-settings">
      ${settings.map(item => `
        <div class="mode-option active">
          <span class="tag ready-tag">${escapeHtml(item.label || "Setting")}</span>
          <b class="row-title">${escapeHtml(item.value || "--")}</b>
          <p>${escapeHtml(item.detail || "")}</p>
        </div>
      `).join("")}
    </div>
    <div class="mode-options">
      ${modes.map(item => `
        <div class="mode-option ${escapeHtml(item.status || "planned")}">
          <span class="tag ${item.status === "active" ? "ready-tag" : ""}">${escapeHtml(item.status || "planned")}</span>
          <b class="row-title">${escapeHtml(item.label || "Mode")}</b>
          <p>${escapeHtml(item.description || "")}</p>
        </div>
      `).join("")}
    </div>
  `;
}

function renderTasks(rows) {
  document.getElementById("tasks").innerHTML = rows.map(item => `
    <div class="task-row">
      <span class="role-chip">${item.role}</span>
      <span>
        <b class="row-title">${item.subject}</b>
        <small class="row-meta">${item.prompt}</small>
        <small class="row-meta task-age">Opened ${escapeHtml(researchTaskAgeLabel(item))}; revalidate against the latest market evidence.</small>
      </span>
    </div>
  `).join("") || `<div class="empty">No open research assignments.</div>`;
}

function closePaperFillDialog() {
  const dialog = document.getElementById("paper-fill-dialog");
  pendingPaperFill = null;
  document.getElementById("paper-fill-confirmation").value = "";
  document.getElementById("paper-fill-submit").disabled = true;
  if (dialog.open) dialog.close();
}

function openPaperFillDialog(proposalId, button) {
  const proposal = (ownerControls?.paper_proposals || [])
    .find(item => item.proposal_id === proposalId);
  if (!proposal) {
    showMessage("The approved paper proposal is no longer available.", true);
    return;
  }

  const expected = `SIMULATE ${proposalId}`;
  pendingPaperFill = { proposalId, expected, button };
  const isSell = proposal.side === "sell";
  const action = proposalActionLabel(proposal);
  document.getElementById("paper-fill-summary").textContent =
    isSell
      ? `This will record a simulated ${action.toUpperCase()} of ${Number(proposal.shares).toFixed(2)} ${proposal.ticker} in the Atlas paper portfolio at the latest available market price.`
      : `This will add a simulated ${proposal.side.toUpperCase()} position of ${Number(proposal.shares).toFixed(2)} ${proposal.ticker} to the Atlas paper portfolio at the latest available market price.`;
  document.getElementById("paper-fill-expected").textContent = expected;
  document.getElementById("paper-fill-confirmation").value = "";
  document.getElementById("paper-fill-submit").disabled = true;
  document.getElementById("paper-fill-submit").textContent =
    isSell ? `Record simulated ${action}` : "Record simulated purchase";
  document.getElementById("paper-fill-dialog").showModal();
  document.getElementById("paper-fill-confirmation").focus();
}

async function submitOwnerAction(action, payload, button) {
  if (button) button.disabled = true;
  try {
    const response = await fetch(`/api/owner/${action}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Atlas-CSRF": ownerControls.csrf_token,
      },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || result.error || "Owner action failed");
    }
    showMessage(
      action === "paper-fill"
        ? `Simulated ${result.result?.action_label || (result.result?.side === "sell" ? "sell" : "purchase")} recorded. Portfolio tracking is active.`
        : action === "paper-policy"
        ? `Atlas paper strategy updated. Auto-manage is ${result.result?.auto_manage_enabled ? "on" : "off"}.`
        : "Owner action saved.",
      false
    );
    await loadDashboard();
  } catch (cause) {
    showMessage(cause.message, true);
  } finally {
    if (button) button.disabled = false;
  }
}

async function applyOwnerAction(button) {
  const action = button.dataset.ownerAction;
  const itemId = button.dataset.itemId;
  const payload = {};
  if (action === "research-decision") {
    payload.task_id = itemId;
    payload.decision = button.dataset.decision;
  } else if (action === "paper-decision") {
    payload.proposal_id = itemId;
    payload.decision = button.dataset.decision;
  } else if (action === "paper-fill") {
    openPaperFillDialog(itemId, button);
    return;
  }
  await submitOwnerAction(action, payload, button);
}

function showMessage(message, isError) {
  const banner = document.getElementById("error-banner");
  banner.textContent = message;
  banner.classList.toggle("success", !isError);
  banner.hidden = false;
  window.setTimeout(() => { banner.hidden = true; }, 4500);
}

async function loadDashboard() {
  const error = document.getElementById("error-banner");
  error.hidden = true;
  setDataFreshness("loading");
  try {
    const fullRequest = fetch("/api/dashboard", { cache: "no-store" });
    const summaryResponse = await fetch("/api/dashboard/summary", { cache: "no-store" });
    if (!summaryResponse.ok) throw new Error(`Dashboard summary request failed (${summaryResponse.status})`);
    const summaryData = await summaryResponse.json();
    renderDashboardSummary(summaryData);
    writeCachedDashboardSummary(summaryData);
    setDataFreshness("loading", "summary loaded");

    const response = await fullRequest;
    if (!response.ok) throw new Error(`Dashboard request failed (${response.status})`);
    const fullData = await response.json();
    renderDashboard(fullData);
    writeCachedDashboardFull(fullData);
    setDataFreshness("live");
  } catch (cause) {
    error.textContent = cause.message;
    error.hidden = false;
    if (!readCachedDashboardFull() && !readCachedDashboardSummary()) {
      setDataFreshness("loading", "retry needed");
    }
  }
}

document.getElementById("refresh").addEventListener("click", loadDashboard);
window.addEventListener("hashchange", () => {
  setActivePage(window.location.hash.replace("#", "") || "overview");
});
document.getElementById("overview").addEventListener("click", event => {
  const jumpButton = event.target.closest("[data-paper-target]");
  if (jumpButton) {
    jumpToPaperTarget(jumpButton.dataset.paperTarget);
  }
});
document.getElementById("recommendations").addEventListener("click", event => {
  const viewButton = event.target.closest("[data-recommendation-view]");
  if (viewButton) {
    setRecommendationView(viewButton.dataset.recommendationView);
    return;
  }
  const jumpButton = event.target.closest("[data-paper-target]");
  if (jumpButton) {
    jumpToPaperTarget(jumpButton.dataset.paperTarget);
  }
});
document.getElementById("research").addEventListener("click", event => {
  const reportFilter = event.target.closest("[data-report-filter]");
  if (reportFilter) {
    reportArchiveFilter = reportFilter.dataset.reportFilter || "all";
    reportArchiveExpanded = false;
    renderReportArchive(reportArchive);
    return;
  }
  const jumpButton = event.target.closest("[data-research-target]");
  if (jumpButton) {
    jumpToResearchTarget(jumpButton.dataset.researchTarget);
  }
});
document.getElementById("universe-search").addEventListener("input", renderUniverseList);
document.getElementById("universe-category").addEventListener("change", renderUniverseList);
document.getElementById("universe-toggle").addEventListener("click", () => {
  universeExpanded = !universeExpanded;
  renderUniverseList();
});
document.getElementById("report-archive-toggle").addEventListener("click", () => {
  reportArchiveExpanded = !reportArchiveExpanded;
  renderReportArchive(reportArchive);
});
document.getElementById("controls").addEventListener("click", event => {
  const jumpButton = event.target.closest("[data-controls-target]");
  if (jumpButton) {
    jumpToControlsTarget(jumpButton.dataset.controlsTarget);
    return;
  }
  const presetButton = event.target.closest("[data-strategy-preset]");
  if (presetButton) {
    applyStrategyPreset(presetButton.dataset.strategyPreset);
    return;
  }
  const button = event.target.closest("[data-owner-action]");
  if (button) applyOwnerAction(button);
});
document.getElementById("access").addEventListener("click", event => {
  const jumpButton = event.target.closest("[data-access-target]");
  if (jumpButton) jumpToAccessTarget(jumpButton.dataset.accessTarget);
});
document.getElementById("controls").addEventListener("submit", async event => {
  const form = event.target.closest("#strategy-policy-form");
  if (!form) return;
  event.preventDefault();
  await submitStrategyPolicy(form);
});
document.getElementById("paper-fill-confirmation").addEventListener("input", event => {
  document.getElementById("paper-fill-submit").disabled =
    !pendingPaperFill || event.target.value !== pendingPaperFill.expected;
});
document.getElementById("paper-fill-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (!pendingPaperFill) return;
  const fill = pendingPaperFill;
  const confirmation = document.getElementById("paper-fill-confirmation").value;
  if (confirmation !== fill.expected) return;
  closePaperFillDialog();
  await submitOwnerAction(
    "paper-fill",
    { proposal_id: fill.proposalId, confirmation },
    fill.button
  );
});
document.getElementById("paper-fill-cancel").addEventListener("click", closePaperFillDialog);
document.getElementById("paper-fill-close").addEventListener("click", closePaperFillDialog);
document.getElementById("paper-fill-dialog").addEventListener("cancel", event => {
  event.preventDefault();
  closePaperFillDialog();
});
document.getElementById("open-trade-history").addEventListener("click", openTradeHistoryDialog);
document.getElementById("trade-history-close").addEventListener("click", closeTradeHistoryDialog);
document.getElementById("trade-history-dialog").addEventListener("cancel", event => {
  event.preventDefault();
  closeTradeHistoryDialog();
});
document.getElementById("open-basis-report").addEventListener("click", openBasisReportDialog);
document.getElementById("basis-report-close").addEventListener("click", closeBasisReportDialog);
document.getElementById("export-basis-report").addEventListener("click", exportBasisReportCsv);
document.getElementById("basis-report-dialog").addEventListener("cancel", event => {
  event.preventDefault();
  closeBasisReportDialog();
});
document.getElementById("paper").addEventListener("click", event => {
  const sectionButton = event.target.closest("[data-paper-section]");
  if (sectionButton) {
    jumpToPaperSection(sectionButton.dataset.paperSection);
    return;
  }
  const jumpButton = event.target.closest("[data-paper-target]");
  if (jumpButton) {
    jumpToPaperTarget(jumpButton.dataset.paperTarget);
    return;
  }
  const button = event.target.closest("[data-position-detail]");
  if (button) {
    openPositionDetailDialog(button.dataset.positionDetail);
  }
});
document.getElementById("position-detail-open-basis").addEventListener("click", () => {
  closePositionDetailDialog();
  openBasisReportDialog();
});
document.getElementById("position-detail-close").addEventListener("click", closePositionDetailDialog);
document.getElementById("position-detail-dialog").addEventListener("cancel", event => {
  event.preventDefault();
  closePositionDetailDialog();
});
renderEnvironment();
initializeHelpPopovers();
setRecommendationView("actions");
setActivePage(window.location.hash.replace("#", "") || "overview");
hydrateDashboardFromCache();
loadDashboard();
