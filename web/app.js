const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
let ownerControls = null;
let pendingPaperFill = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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
  renderCorporateActions(data.corporate_actions || []);
  renderThesisOverview(paper.thesis_overview || {});
  renderPositions(paper.positions || []);
  renderPaperActivity(paper.activity || []);
  renderPaperOperatingMode(paper.operating_mode || {});
  renderPaperFeedbackSummary(paper.feedback_summary || {});
  renderPaperFeedback(paper.feedback || []);
  renderRecommendationSummary(data.owner_controls?.paper_proposals || [], data.watchlist || []);
  renderRecommendations(data.owner_controls?.paper_proposals || [], data.watchlist || []);
  renderTasks(data.research?.tasks || []);
  renderOwnerControls(data.owner_controls || null);
  renderAccess(data.access || {});
  renderWorkspace(data.workspace || null);
}

function recommendationStageLabel(item) {
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

function renderRecommendationSummary(proposals, watchlist) {
  const rows = proposals || [];
  const summary = {
    buyPending: rows.filter(item => item.side === "buy" && item.status === "pending").length,
    buyReady: rows.filter(item => item.side === "buy" && item.status === "approved").length,
    reduce: rows.filter(item => item.side === "sell").length,
    tracked: (watchlist || []).length,
  };
  const highlights = rows
    .slice()
    .sort((left, right) => recommendationRank(left) - recommendationRank(right))
    .slice(0, 3);

  document.getElementById("recommendation-summary").innerHTML = `
    <div class="recommendation-summary-grid">
      <div class="recommendation-summary-card">
        <span class="summary-label">Buy candidates</span>
        <strong>${summary.buyPending}</strong>
        <small>Need owner approval</small>
      </div>
      <div class="recommendation-summary-card ready">
        <span class="summary-label">Ready to simulate</span>
        <strong>${summary.buyReady}</strong>
        <small>Approved, waiting for Simulate fill</small>
      </div>
      <div class="recommendation-summary-card exit">
        <span class="summary-label">Reduce / exit</span>
        <strong>${summary.reduce}</strong>
        <small>Paper risk reviews in force</small>
      </div>
      <div class="recommendation-summary-card tracked">
        <span class="summary-label">Tracked list</span>
        <strong>${summary.tracked}</strong>
        <small>Universe names under coverage</small>
      </div>
    </div>
    <div class="recommendation-summary-focus">
      <span class="access-label">Atlas focus right now</span>
      <div class="recommendation-focus-list">
        ${highlights.length ? highlights.map(item => `
          <div class="recommendation-focus-row">
            <span class="thesis-badge ${recommendationStageClass(item)}">${escapeHtml(recommendationStageLabel(item))}</span>
            <div>
              <b class="row-title">${escapeHtml(item.ticker || "Proposal")}</b>
              <small class="row-meta">${escapeHtml((item.rationale || [item.thesis || "Awaiting rationale."])[0] || "Awaiting rationale.")}</small>
            </div>
          </div>
        `).join("") : `<div class="empty">No active Atlas paper recommendations right now.</div>`}
      </div>
    </div>
  `;
}

function setActivePage(pageId) {
  const target = pageId || "overview";
  document.querySelectorAll(".dashboard-page").forEach(page => {
    page.classList.toggle("active-page", page.dataset.page === target);
  });
  document.querySelectorAll(".nav-item").forEach(link => {
    link.classList.toggle("active", link.getAttribute("href") === `#${target}`);
  });
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
  document.getElementById("phase-progress-bar").style.width = `${completion}%`;
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
  const buyCount = proposals.filter(item => item.side === "buy").length;
  const sellCount = proposals.filter(item => item.side === "sell").length;
  const actions = controls.daily_action_list || [];
  const outcomes = controls.owner_outcomes || {};
  document.getElementById("research-review-count").textContent =
    `${reviews.length} awaiting review`;
  document.getElementById("paper-proposal-count").textContent =
    `${buyCount} buy / ${sellCount} exit-trim`;
  renderRecommendations(proposals, null);
  renderOwnerOutcomes(outcomes);
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
  `).join("") || `<div class="empty">No daily owner actions are awaiting review.</div>`;
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
          <button type="button" data-owner-action="research-decision" data-item-id="${escapeHtml(item.id)}" data-decision="approve">Approve</button>
          <button type="button" class="secondary" data-owner-action="research-decision" data-item-id="${escapeHtml(item.id)}" data-decision="defer">Defer</button>
          <button type="button" class="danger" data-owner-action="research-decision" data-item-id="${escapeHtml(item.id)}" data-decision="reject">Reject</button>
        </div>
      </article>`;
  }).join("") || `<div class="empty">No research recommendations await your decision.</div>`;

  document.getElementById("paper-proposals").innerHTML = proposals.map(item => {
    const review = item.risk_review || {};
    const approved = item.status === "approved";
    return `
      <article class="decision-row">
        <div>
          <span class="tag ${item.side === "buy" ? "buy-tag" : "exit-tag"}">${escapeHtml(item.status)}</span>
          <b class="row-title">${proposalControlTitle(item)}</b>
          <small class="row-meta">Reference ${money.format(Number(item.reference_price) || 0)} · Risk ${escapeHtml(review.verdict || "pending")}</small>
          <p>${escapeHtml(item.thesis || "No thesis supplied.")}</p>
          ${proposalImpact(item)}
          ${renderRationale(item.rationale, item)}
          <small class="row-meta">Workflow: approve the paper idea first, then use Simulate fill to record the hypothetical ${proposalActionLabel(item)} in Atlas paper tracking.</small>
        </div>
        <div class="decision-actions">
          ${approved ? `
            <button type="button" class="simulate-button" data-owner-action="paper-fill" data-item-id="${escapeHtml(item.proposal_id)}">Simulate fill</button>
          ` : `
            <button type="button" data-owner-action="paper-decision" data-item-id="${escapeHtml(item.proposal_id)}" data-decision="approve">Approve</button>
            <button type="button" class="danger" data-owner-action="paper-decision" data-item-id="${escapeHtml(item.proposal_id)}" data-decision="reject">Reject</button>
          `}
        </div>
      </article>`;
  }).join("") || `<div class="empty">No paper proposals require action.</div>`;
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

function proposalControlTitle(item) {
  if (item.side === "sell") {
    return `${escapeHtml(proposalActionLabel(item).toUpperCase())} ${Number(item.shares).toFixed(2)} ${escapeHtml(item.ticker)}`;
  }
  return `${escapeHtml(item.side).toUpperCase()} ${Number(item.shares).toFixed(2)} ${escapeHtml(item.ticker)}`;
}

function renderRecommendations(proposals, watchlist) {
  const buyProposals = (proposals || [])
    .filter(item => item.side === "buy")
    .sort((left, right) => recommendationRank(left) - recommendationRank(right));
  const sellProposals = (proposals || [])
    .filter(item => item.side === "sell")
    .sort((left, right) => recommendationRank(left) - recommendationRank(right));
  const buyHtml = buyProposals.map(item => `
    <article class="recommendation-row ${item.status === "approved" ? "approved-rec" : ""}">
      <span class="tag ${item.status === "approved" ? "ready-tag" : "buy-tag"}">${escapeHtml(recommendationStageLabel(item))}</span>
      <div>
        <b class="row-title">${proposalHeadline(item)}</b>
        <small class="row-meta">Reference ${money.format(Number(item.reference_price) || 0)} - ${escapeHtml(item.thesis || "No thesis supplied.")}</small>
        <small class="row-meta">${item.status === "approved" ? "Status: approved by owner and ready for Simulate fill." : "Status: Atlas recommends this idea, but it still needs owner approval."}</small>
        ${renderRationale(item.rationale, item)}
        <small class="row-meta">${item.status === "approved" ? "Next step: use Simulate fill to add this to the paper portfolio." : "Next step: approve or reject this paper proposal in Controls."}</small>
      </div>
    </article>
  `).join("") || `<div class="empty">No current paper purchase recommendations. Future Atlas-generated proposals will include a Why now rationale before any owner decision.</div>`;
  ["recommended-buys", "overview-recommended-buys"].forEach(id => {
    const target = document.getElementById(id);
    if (target) target.innerHTML = buyHtml;
  });
  const sellHtml = sellProposals.map(item => `
    <article class="recommendation-row exit-rec ${item.status === "approved" ? "approved-rec" : ""}">
      <span class="tag exit-tag">${escapeHtml(recommendationStageLabel(item))}</span>
      <div>
        <b class="row-title">${proposalHeadline(item)}</b>
        <small class="row-meta">Reference ${money.format(Number(item.reference_price) || 0)} - ${escapeHtml(item.thesis || "No thesis supplied.")}</small>
        <small class="row-meta">Status: Atlas wants to ${escapeHtml(proposalActionLabel(item))} simulated exposure in this holding.</small>
        ${proposalImpact(item)}
        ${renderRationale(item.rationale, item)}
        <small class="row-meta">${item.status === "approved" ? `Next step: use Simulate fill to record this simulated ${proposalActionLabel(item)}.` : `Next step: approve or reject this simulated ${proposalActionLabel(item)} proposal in Controls.`}</small>
      </div>
    </article>
  `).join("") || `<div class="empty">No current paper exit or trim recommendations. Atlas will surface one here if an open simulated position weakens.</div>`;
  ["recommended-exits", "overview-recommended-exits"].forEach(id => {
    const target = document.getElementById(id);
    if (target) target.innerHTML = sellHtml;
  });

  if (watchlist === null) return;
  const fullRows = (watchlist || []).slice(0, 80).map(item => `
    <div class="watchlist-item ${item.category === "Core" ? "core" : item.category === "Watchlist" ? "watchlist" : "tracked"}">
      <b>${escapeHtml(item.ticker)}</b>
      <span>${escapeHtml(item.category || "Tracked")}</span>
      <small>${escapeHtml(item.sector || "Unclassified")}${item.score === null || item.score === undefined ? "" : ` - score ${Number(item.score).toFixed(1)}`}</small>
    </div>
  `).join("") || `<div class="empty">No tracked securities are available in the latest run.</div>`;
  const previewRows = (watchlist || []).slice(0, 12).map(item => `
    <div class="watchlist-item compact">
      <b>${escapeHtml(item.ticker)}</b>
      <span>${escapeHtml(item.category || "Tracked")}</span>
    </div>
  `).join("") || `<div class="empty">No tracked securities available.</div>`;
  const fullTarget = document.getElementById("current-watchlist");
  const previewTarget = document.getElementById("overview-current-list");
  if (fullTarget) fullTarget.innerHTML = fullRows;
  if (previewTarget) previewTarget.innerHTML = previewRows;
}

function renderRationale(rationale, item = {}) {
  const rows = (rationale || []).filter(Boolean);
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

function renderPositions(rows) {
  document.getElementById("positions").innerHTML = rows.map(item => {
    const review = item.review || {};
    const thesis = item.thesis_status || { label: "healthy", summary: "Awaiting the next daily thesis review." };
    return `
      <div class="position-row">
        <span>
          <b class="row-title">${item.ticker} · ${Number(item.shares).toFixed(0)} shares</b>
          <small class="row-meta">Average ${money.format(item.average_cost)} · ${review.verdict || "unreviewed"} thesis</small>
          <small class="row-meta thesis-summary"><span class="thesis-badge ${escapeHtml(thesis.label)}">${escapeHtml(thesis.label)}</span>${escapeHtml(thesis.summary || "")}</small>
        </span>
        <span>
          <b class="row-title">${money.format(item.market_value || 0)}</b>
          <small class="row-meta ${changeClass(item.unrealized_gain_loss)}">${money.format(item.unrealized_gain_loss || 0)}</small>
        </span>
      </div>`;
  }).join("") || `<div class="empty">No open simulated positions.</div>`;
}

function renderPaperFeedback(rows) {
  document.getElementById("paper-feedback").innerHTML = rows.map(item => {
    const verdict = String(item.verdict || "not_enough_time");
    const action = String(item.action_label || (item.side === "sell" ? "sell" : "purchase"));
    const sideContext = item.side === "sell"
      ? `Post-sell move ${signed(item.security_return_pct)}`
      : `Return ${signed(item.security_return_pct)}`;
    const benchmarkText = ["SPY", "QQQ"].map(ticker => {
      const value = item.benchmark_returns_pct?.[ticker];
      return `${ticker} ${signed(value)}`;
    }).join(" · ");
    return `
      <article class="feedback-row ${escapeHtml(verdict)}">
        <div>
          <span class="tag verdict-tag">${escapeHtml(verdict).replaceAll("_", " ")}</span>
          <b class="row-title">${item.side === "sell" ? `${escapeHtml(item.ticker)} simulated ${escapeHtml(String(item.action_label || "sell"))}` : `${escapeHtml(item.ticker)} simulated buy`}</b>
          <small class="row-meta">Fill ${money.format(Number(item.fill_price) || 0)}${item.latest_price === null || item.latest_price === undefined ? "" : ` · latest ${money.format(Number(item.latest_price) || 0)}`}</small>
          <p>${escapeHtml(item.summary || "Atlas is waiting for enough evidence to judge this idea.")}</p>
          <small class="row-meta">${sideContext} · ${benchmarkText} · ${Number(item.snapshots || 0).toFixed(0)} snapshots</small>
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

function renderPaperActivity(rows) {
  document.getElementById("paper-activity").innerHTML = rows.map(item => {
    const action = String(item.action_label || item.side || "activity");
    const rationale = item.rationale || [];
    const whyHeading = action === "trim" ? "Why trim" : action === "exit" ? "Why exit" : "Why buy";
    return `
      <article class="activity-row ${escapeHtml(item.side || "buy")}">
        <div>
          <span class="tag ${item.side === "sell" ? "exit-tag" : "buy-tag"}">${escapeHtml(action).replaceAll("_", " ")}</span>
          <b class="row-title">${escapeHtml(item.title || "Atlas activity")}</b>
          <small class="row-meta">${new Date(item.timestamp).toLocaleString()} · ${Number(item.shares || 0).toFixed(2)} shares · ${money.format(Number(item.fill_price) || 0)}</small>
          <p>${escapeHtml(item.summary || "Atlas recorded a simulated trade.")}</p>
          ${item.side === "sell" ? `<small class="row-meta ${changeClass(item.realized_gain_loss)}">Realized result ${money.format(Number(item.realized_gain_loss) || 0)}</small>` : ""}
          <small class="row-meta">Thesis: ${escapeHtml(item.thesis || "No thesis supplied.")}</small>
          ${rationale.length ? `<div class="why-now compact"><span>${whyHeading}</span><ul>${rationale.slice(0, 3).map(reason => `<li>${escapeHtml(reason)}</li>`).join("")}</ul></div>` : ""}
        </div>
      </article>`;
  }).join("") || `<div class="empty">No simulated buys or sells have been recorded yet.</div>`;
}

function renderPaperOperatingMode(mode) {
  const current = mode.current || {};
  const modes = mode.modes || [];
  document.getElementById("paper-operating-mode").innerHTML = `
    <div class="mode-current">
      <span class="access-label">Current mode</span>
      <strong>${escapeHtml(current.label || "Recommendation mode")}</strong>
      <p>${escapeHtml(current.description || "Atlas is currently operating as a recommendation engine.")}</p>
      <small>${escapeHtml(mode.boundary || "Real-money trading remains disabled.")}</small>
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
      <span><b class="row-title">${item.subject}</b><small class="row-meta">${item.prompt}</small></span>
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
  button.disabled = true;
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
        : "Owner action saved.",
      false
    );
    await loadDashboard();
  } catch (cause) {
    showMessage(cause.message, true);
  } finally {
    button.disabled = false;
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
window.addEventListener("hashchange", () => {
  setActivePage(window.location.hash.replace("#", "") || "overview");
});
document.getElementById("controls").addEventListener("click", event => {
  const button = event.target.closest("[data-owner-action]");
  if (button) applyOwnerAction(button);
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
renderEnvironment();
initializeHelpPopovers();
setActivePage(window.location.hash.replace("#", "") || "overview");
loadDashboard();
