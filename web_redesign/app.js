const prototypeSnapshot = {
  label: "Illustrative sample snapshot",
  asOf: "August 28, 2026 at 4:00 PM PT",
  session: "Friday market close",
  source: "Design fixtures, not a live market feed"
};

const securities = [
  { ticker: "NVDA", name: "NVIDIA", sector: "Semiconductors", exchange: "NASDAQ", score: 94, price: 182.74, move: 2.8, action: "Buy", conviction: "High", catalyst: "Blackwell demand", risk: "Premium valuation", targetWeight: 5, preferredRange: "$176-$184", thesisTitle: "AI infrastructure leadership remains durable.", thesis: "NVIDIA combines category leadership, expanding software economics, and strong balance-sheet quality. Improving semiconductor breadth supports the setup, while valuation keeps the proposed paper position deliberately limited.", whyNow: "Price is inside the preferred range and estimate revisions remain constructive.", invalidation: "Hyperscaler capital spending slows materially or gross margins deteriorate for two consecutive reviews.", scores: { Growth: 97, Quality: 93, Moat: 96, Momentum: 89, Risk: 76 }, growth: { Revenue: "+42%", EPS: "+51%", FCF: "+36%" }, valuation: [["Forward P/E", "36.4x", "5-year range 24x-72x"], ["EV / Sales", "18.2x", "Peer median 12.8x"], ["FCF yield", "2.1%", "5-year median 2.4%"]], return1y: 34.7, evidence: ["Large cloud buyer expanded accelerator orders", "Consensus EPS estimate increased 2.3%", "Latest filing evidence incorporated"] },
  { ticker: "MSFT", name: "Microsoft", sector: "Software", exchange: "NASDAQ", score: 91, price: 536.12, move: 0.9, action: "Buy", conviction: "High", catalyst: "Azure AI growth", risk: "AI capex intensity", targetWeight: 14, preferredRange: "$515-$540", thesisTitle: "Cloud distribution strengthens the AI platform advantage.", thesis: "Microsoft pairs durable enterprise distribution with accelerating Azure AI demand and recurring software cash flow. The paper portfolio already owns the company, so Atlas favors measured additions rather than a new full position.", whyNow: "Azure growth and forward estimates improved while price remains near the preferred accumulation range.", invalidation: "AI infrastructure spending rises without corresponding cloud revenue or margin improvement.", scores: { Growth: 91, Quality: 96, Moat: 95, Momentum: 86, Risk: 78 }, growth: { Revenue: "+16%", EPS: "+18%", FCF: "+14%" }, valuation: [["Forward P/E", "32.8x", "5-year range 24x-38x"], ["EV / Sales", "12.1x", "Peer median 9.6x"], ["FCF yield", "2.7%", "5-year median 3.1%"]], return1y: 22.4, evidence: ["Azure AI consumption remained above plan", "Commercial bookings estimates moved higher", "Cloud margin guidance was maintained"] },
  { ticker: "AVGO", name: "Broadcom", sector: "Semiconductors", exchange: "NASDAQ", score: 89, price: 316.84, move: 1.7, action: "Watch", conviction: "Medium", catalyst: "Custom accelerator demand", risk: "Integration execution", targetWeight: 13, preferredRange: "$292-$305", thesisTitle: "Custom silicon demand broadens semiconductor exposure.", thesis: "Broadcom offers differentiated exposure to custom AI accelerators, networking, and infrastructure software. Atlas is constructive, but the paper position is already near its target and the sample price is above the preferred range.", whyNow: "Customer demand remains strong, but current price is above the preferred range.", invalidation: "Custom accelerator growth slows or infrastructure software integration misses cash-flow targets.", scores: { Growth: 92, Quality: 88, Moat: 91, Momentum: 87, Risk: 72 }, growth: { Revenue: "+24%", EPS: "+19%", FCF: "+21%" }, valuation: [["Forward P/E", "31.6x", "5-year range 16x-33x"], ["EV / Sales", "17.4x", "Peer median 12.8x"], ["FCF yield", "2.5%", "5-year median 3.4%"]], return1y: 41.2, evidence: ["Custom accelerator pipeline expanded", "Networking demand remained firm", "Integration savings tracked ahead of plan"] },
  { ticker: "CRWD", name: "CrowdStrike", sector: "Cybersecurity", exchange: "NASDAQ", score: 87, price: 471.36, move: -0.6, action: "Watch", conviction: "Medium", catalyst: "Platform consolidation", risk: "Multiple compression", targetWeight: 4, preferredRange: "$430-$455", thesisTitle: "Platform consolidation supports durable security growth.", thesis: "CrowdStrike continues to expand modules per customer and benefits as enterprises consolidate security tools. Atlas wants confirmation that valuation and execution risk are adequately reflected before opening a paper position.", whyNow: "Fundamental evidence remains positive, but price confirmation is incomplete.", invalidation: "Net retention weakens materially or platform adoption fails to offset pricing pressure.", scores: { Growth: 90, Quality: 85, Moat: 88, Momentum: 81, Risk: 70 }, growth: { Revenue: "+22%", EPS: "+27%", FCF: "+24%" }, valuation: [["Forward P/E", "58.3x", "5-year range 42x-96x"], ["EV / Sales", "17.8x", "Peer median 11.4x"], ["FCF yield", "1.8%", "5-year median 1.5%"]], return1y: 18.6, evidence: ["Module adoption continued to expand", "Net-new ARR remained resilient", "Channel checks were constructive"] },
  { ticker: "PLTR", name: "Palantir", sector: "Software", exchange: "NASDAQ", score: 85, price: 152.20, move: 3.1, action: "Hold", conviction: "Medium", catalyst: "Commercial acceleration", risk: "Valuation concentration", targetWeight: 9, preferredRange: "$132-$145", thesisTitle: "Commercial adoption validates the AI software platform.", thesis: "Palantir is converting AI demand into faster commercial growth and improving margins. The paper portfolio holds a full-sized position, so Atlas recommends holding while monitoring valuation concentration.", whyNow: "Operating momentum is strong, but the position is already close to its target allocation.", invalidation: "Commercial growth decelerates sharply or remaining-deal value fails to convert into revenue.", scores: { Growth: 94, Quality: 84, Moat: 87, Momentum: 93, Risk: 55 }, growth: { Revenue: "+31%", EPS: "+37%", FCF: "+29%" }, valuation: [["Forward P/E", "71.2x", "5-year range 39x-91x"], ["EV / Sales", "34.6x", "Peer median 12.4x"], ["FCF yield", "1.1%", "5-year median 1.6%"]], return1y: 76.1, evidence: ["US commercial growth accelerated", "Contract value expanded", "Margins improved despite hiring"] },
  { ticker: "LMT", name: "Lockheed Martin", sector: "Aerospace & Defense", exchange: "NYSE", score: 82, price: 498.18, move: -1.2, action: "Hold", conviction: "Medium", catalyst: "Backlog conversion", risk: "Program timing", targetWeight: 8, preferredRange: "$475-$505", thesisTitle: "Backlog supports a durable defense cash-flow profile.", thesis: "Lockheed Martin adds portfolio diversification through a large funded backlog and durable government demand. Atlas favors holding the existing paper position while monitoring program timing and cash conversion.", whyNow: "The valuation is reasonable and defense exposure offsets technology concentration.", invalidation: "Material program charges recur or backlog conversion falls below the current planning range.", scores: { Growth: 73, Quality: 87, Moat: 91, Momentum: 68, Risk: 81 }, growth: { Revenue: "+6%", EPS: "+8%", FCF: "+9%" }, valuation: [["Forward P/E", "18.4x", "5-year range 15x-21x"], ["EV / Sales", "1.9x", "Peer median 2.1x"], ["FCF yield", "5.2%", "5-year median 4.8%"]], return1y: 9.8, evidence: ["Backlog remained near a record level", "Missile demand stayed elevated", "Cash-flow outlook was reaffirmed"] },
  { ticker: "AMZN", name: "Amazon", sector: "Consumer & Cloud", exchange: "NASDAQ", score: 80, price: 229.41, move: -2.4, action: "Trim", conviction: "Medium", catalyst: "AWS reacceleration", risk: "Margin normalization", targetWeight: 6, preferredRange: "$208-$222", thesisTitle: "AWS strength remains intact, but position size is elevated.", thesis: "Amazon retains strong cloud and commerce advantages, but the current paper position exceeds its target while near-term retail margins normalize. Atlas recommends trimming exposure rather than abandoning the thesis.", whyNow: "Relative momentum softened while the simulated position remained above its 6% target.", invalidation: "AWS growth reaccelerates with improving margins and the position falls back within policy limits.", scores: { Growth: 86, Quality: 82, Moat: 92, Momentum: 67, Risk: 69 }, growth: { Revenue: "+12%", EPS: "+21%", FCF: "+18%" }, valuation: [["Forward P/E", "31.2x", "5-year range 29x-74x"], ["EV / Sales", "3.4x", "Peer median 4.1x"], ["FCF yield", "2.8%", "5-year median 2.0%"]], return1y: 14.3, evidence: ["AWS growth held above expectations", "Retail margins normalized", "Position weight remained above target"] },
  { ticker: "META", name: "Meta Platforms", sector: "Communication", exchange: "NASDAQ", score: 74, price: 681.32, move: -3.6, action: "Exit", conviction: "High", catalyst: "Ad efficiency", risk: "Capital spending", targetWeight: 0, preferredRange: "No active entry range", thesisTitle: "Risk controls now outweigh the advertising thesis.", thesis: "Meta's advertising engine remains productive, but weakening estimate momentum and rising capital intensity triggered the current paper exit rule. Atlas prioritizes process discipline over waiting for a rebound.", whyNow: "The position breached the paper risk threshold after three consecutive weak observations.", invalidation: "Estimate momentum recovers and capital-spending returns become measurable enough to rebuild the score.", scores: { Growth: 82, Quality: 89, Moat: 90, Momentum: 49, Risk: 48 }, growth: { Revenue: "+14%", EPS: "+11%", FCF: "+7%" }, valuation: [["Forward P/E", "24.7x", "5-year range 14x-29x"], ["EV / Sales", "8.6x", "Peer median 6.9x"], ["FCF yield", "3.0%", "5-year median 3.8%"]], return1y: 11.7, evidence: ["Estimate momentum weakened again", "Capital-spending expectations increased", "Relative strength breached the risk threshold"] }
];

const paperAccount = {
  cash: 31460,
  startingValue: 100000,
  positions: [
    { ticker: "MSFT", shares: 24, averageCost: 498.20 },
    { ticker: "AVGO", shares: 42, averageCost: 292.10 },
    { ticker: "PLTR", shares: 60, averageCost: 139.45 },
    { ticker: "LMT", shares: 18, averageCost: 486.30 },
    { ticker: "AMZN", shares: 50, averageCost: 234.35 },
    { ticker: "META", shares: 26, averageCost: 704.10 }
  ]
};

const heldTickers = new Set(paperAccount.positions.map(position => position.ticker));
securities.forEach(item => { item.owned = heldTickers.has(item.ticker); });

const alerts = [
  { severity: "High", title: "META breached Atlas risk threshold", detail: "Relative strength and estimate momentum weakened for a third observation.", time: "18 min ago", icon: "triangle-alert" },
  { severity: "Medium", title: "NVDA entered the buy range", detail: "Price is within 1.8% of Atlas's preferred entry zone with strong confirmation.", time: "42 min ago", icon: "circle-dollar-sign" },
  { severity: "Medium", title: "AMZN position exceeds target weight", detail: "The simulated position is 10.9%, above its 6% target.", time: "2 hr ago", icon: "scale" }
];

const reports = [
  { type: "Morning brief", title: "AI leadership broadens as market breadth improves", date: "Aug 29, 2026", read: "4 min" },
  { type: "Opportunity report", title: "NVIDIA: confirmation strengthens near entry range", date: "Aug 28, 2026", read: "7 min" },
  { type: "Risk alert", title: "Meta: weakening relative strength merits review", date: "Aug 28, 2026", read: "3 min" },
  { type: "Weekly strategy", title: "Cash remains high while quality leadership narrows", date: "Aug 23, 2026", read: "9 min" },
  { type: "Portfolio review", title: "Software contribution offsets consumer weakness", date: "Aug 22, 2026", read: "6 min" }
];

const pageContent = document.getElementById("page-content");
const searchInput = document.getElementById("global-search");
const searchResults = document.getElementById("search-results");
let toastTimer;

const icon = (name) => `<i data-lucide="${name}"></i>`;
const signed = (value) => `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(2)}%`;
const money = (value, decimals = 0) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value);
const percent = (value, decimals = 1) => `${Number(value).toFixed(decimals)}%`;
const actionClass = (action) => action === "Buy" ? "buy" : action === "Exit" || action === "Trim" ? "sell" : "watch";
const researchUrl = (ticker, tab = "overview") => `#research/${ticker}/${tab}`;
const decisionUrl = (ticker, step = "impact") => `#decision/${ticker}/${step}`;

function portfolioSnapshot() {
  const positions = paperAccount.positions.map(position => {
    const security = securities.find(item => item.ticker === position.ticker);
    const marketValue = position.shares * security.price;
    const costBasis = position.shares * position.averageCost;
    return {
      ...position,
      security,
      marketValue,
      costBasis,
      unrealized: marketValue - costBasis,
      dayChange: marketValue * (security.move / 100)
    };
  });
  const invested = positions.reduce((sum, position) => sum + position.marketValue, 0);
  const costBasis = positions.reduce((sum, position) => sum + position.costBasis, 0);
  const totalValue = invested + paperAccount.cash;
  const unrealized = invested - costBasis;
  const dayChange = positions.reduce((sum, position) => sum + position.dayChange, 0);
  return { positions, invested, costBasis, totalValue, unrealized, dayChange, cashWeight: paperAccount.cash / totalValue * 100 };
}

function positionFor(ticker) {
  return portfolioSnapshot().positions.find(position => position.ticker === ticker);
}

function decisionPreview(item) {
  const portfolio = portfolioSnapshot();
  const position = portfolio.positions.find(candidate => candidate.ticker === item.ticker);
  const currentValue = position?.marketValue || 0;
  const targetValue = portfolio.totalValue * item.targetWeight / 100;
  let side = "None";
  let shares = 0;

  if (item.action === "Buy" && targetValue > currentValue) {
    side = "Buy";
    shares = Math.floor((targetValue - currentValue) / item.price);
  } else if (item.action === "Trim" && currentValue > targetValue) {
    side = "Sell";
    shares = Math.min(position?.shares || 0, Math.ceil((currentValue - targetValue) / item.price));
  } else if (item.action === "Exit" && position) {
    side = "Sell";
    shares = position.shares;
  }

  const estimatedValue = shares * item.price;
  const projectedPositionValue = side === "Buy" ? currentValue + estimatedValue : side === "Sell" ? Math.max(0, currentValue - estimatedValue) : currentValue;
  const projectedCash = side === "Buy" ? paperAccount.cash - estimatedValue : side === "Sell" ? paperAccount.cash + estimatedValue : paperAccount.cash;
  const projectedWeight = projectedPositionValue / portfolio.totalValue * 100;
  const projectedCashWeight = projectedCash / portfolio.totalValue * 100;
  const instruction = side === "Buy" ? `Buy ${shares} simulated shares` : side === "Sell" && item.action === "Exit" ? `Exit ${shares} simulated shares` : side === "Sell" ? `Trim ${shares} simulated shares` : "No simulated transaction proposed";

  return {
    item,
    portfolio,
    position,
    side,
    shares,
    estimatedValue,
    currentValue,
    currentWeight: currentValue / portfolio.totalValue * 100,
    projectedPositionValue,
    projectedCash,
    projectedWeight,
    projectedCashWeight,
    instruction,
    actionable: shares > 0,
    checks: [
      { label: "Paper authority only", detail: "The design contains no brokerage connection or real-order path.", passed: true },
      { label: "Recommendation is actionable", detail: shares > 0 ? `${item.action} produces a non-zero simulated share estimate.` : `${item.action} does not require a transaction at this sample price.`, passed: shares > 0 },
      { label: "Minimum cash reserve", detail: `${percent(projectedCashWeight)} projected cash versus a 20% minimum.`, passed: projectedCashWeight >= 20 },
      { label: "Maximum position size", detail: `${percent(projectedWeight)} projected weight versus a 15% limit.`, passed: projectedWeight <= 15 },
      { label: "Fresh server validation", detail: "Required when this screen is connected to Atlas. Not available in the static prototype.", passed: false, blocked: true }
    ]
  };
}

function dataStatus() {
  return `<div class="data-status" role="note">${icon("flask-conical")}<div><strong>${prototypeSnapshot.label}</strong><span>${prototypeSnapshot.asOf} · ${prototypeSnapshot.session} · ${prototypeSnapshot.source}</span></div></div>`;
}
const pageHeading = (eyebrow, title, detail, actions = "") => `
  ${dataStatus()}
  <header class="page-heading">
    <div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p>${detail}</p></div>
    ${actions ? `<div class="heading-actions">${actions}</div>` : ""}
  </header>`;

function tickerCell(item) {
  return `<div class="ticker"><span class="ticker-logo">${item.ticker.slice(0, 2)}</span><div><b>${item.ticker}</b><small>${item.name}</small></div></div>`;
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 2600);
}

function recommendationsTable(items = securities) {
  return `<div class="panel table-panel">
    <div class="panel-heading"><div><h2>Atlas recommendations</h2><p>Ranked by conviction, evidence quality, and portfolio fit</p></div><button class="button" data-go="discover">View all ${icon("arrow-right")}</button></div>
    <table class="data-table"><thead><tr><th>Security</th><th>Action</th><th>Atlas Score</th><th>Price</th><th>Today</th><th>Primary catalyst</th><th>Position</th><th></th></tr></thead>
    <tbody>${items.map(item => `<tr>
      <td>${tickerCell(item)}</td><td><span class="tag ${actionClass(item.action)}">${item.action}</span></td><td><span class="score">${item.score}</span></td>
      <td>$${item.price.toFixed(2)}</td><td class="${item.move >= 0 ? "positive" : "negative"}">${signed(item.move)}</td><td>${item.catalyst}</td>
      <td>${item.owned ? "Current holding" : "Not owned"}</td><td><button class="icon-button" data-security="${item.ticker}" aria-label="Research ${item.ticker}">${icon("chevron-right")}</button></td>
    </tr>`).join("")}</tbody></table></div>`;
}

function renderToday() {
  const portfolio = portfolioSnapshot();
  const primary = securities[0];
  const totalReturn = (portfolio.totalValue / paperAccount.startingValue - 1) * 100;
  const dayReturn = portfolio.dayChange / (portfolio.totalValue - portfolio.dayChange) * 100;
  const benchmarkEdge = totalReturn - 6.08;
  pageContent.innerHTML = pageHeading("Sample close · Friday, August 28", "Your Atlas decision brief", "The recommendation, portfolio effect, and risks that deserve attention.", `
    <button class="button">${icon("calendar-days")} Upcoming events</button><button class="button primary" data-go="reports">${icon("notebook-text")} Morning brief</button>`)
    + `<section class="panel decision-brief">
      <div class="brief-main"><span class="tag buy">Primary paper recommendation</span><h2>Add ${primary.name} near ${primary.preferredRange}.</h2><p>${primary.thesis}</p><div class="brief-actions"><button class="button primary" data-security="${primary.ticker}">Review evidence</button><button class="button" data-watch="${primary.ticker}">Add to prototype watchlist</button></div><small class="decision-note">This is a sample paper recommendation. It cannot place an order.</small></div>
      <div class="brief-side"><div><span>Action</span><strong>${primary.action} · not currently owned</strong></div><div><span>Atlas Score</span><strong>${primary.score} / 100</strong></div><div><span>Evidence confidence</span><strong>${primary.conviction}</strong></div><div><span>Preferred range</span><strong>${primary.preferredRange}</strong></div><div><span>Proposed paper weight</span><strong>${percent(primary.targetWeight)}</strong></div><div><span>Portfolio effect</span><strong>Cash falls to about ${percent(portfolio.cashWeight - primary.targetWeight)}</strong></div><div><span>Invalidation trigger</span><strong>${primary.risk}</strong></div></div>
    </section><div class="spacer"></div>
    <section class="grid cols-4">
      <article class="panel metric"><small>Paper portfolio</small><strong>${money(portfolio.totalValue)}</strong><span class="${totalReturn >= 0 ? "positive" : "negative"}">${signed(totalReturn)} since start</span></article>
      <article class="panel metric"><small>Last session</small><strong>${money(portfolio.dayChange)}</strong><span class="${dayReturn >= 0 ? "positive" : "negative"}">${signed(dayReturn)} at sample close</span></article>
      <article class="panel metric"><small>Available cash</small><strong>${money(paperAccount.cash)}</strong><span>${percent(portfolio.cashWeight)} of portfolio</span></article>
      <article class="panel metric"><small>Benchmark edge</small><strong>${signed(benchmarkEdge)}</strong><span class="${benchmarkEdge >= 0 ? "positive" : "negative"}">${benchmarkEdge >= 0 ? "Ahead of" : "Behind"} SPY since start</span></article>
    </section><div class="spacer"></div>
    ${recommendationsTable(securities.slice(0, 5))}<div class="spacer"></div>
    <section class="grid two-one">
      <article class="panel"><div class="panel-heading"><div><h2>Portfolio performance</h2><p>Atlas paper portfolio versus SPY (S&amp;P 500) and QQQ (Nasdaq-100)</p></div><div class="segment-control"><button class="active" data-period="1M">1M</button><button data-period="3M">3M</button><button data-period="1Y">1Y</button><button data-period="ALL">All</button></div></div><div class="chart-wrap"><canvas id="performance-chart"></canvas><div class="chart-legend"><span><i class="legend-dot"></i>Atlas ${signed(totalReturn)}</span><span><i class="legend-dot spy"></i>SPY +6.08%</span><span><i class="legend-dot qqq"></i>QQQ +5.44%</span></div></div></article>
      <article class="panel"><div class="panel-heading"><div><h2>Needs attention</h2><p>Current risks and owner decisions</p></div><button class="button" data-go="alerts">All alerts</button></div><div class="panel-body list">${alerts.map(alert => `<div class="list-row"><span class="list-icon ${alert.severity === "High" ? "negative" : "warning"}">${icon(alert.icon)}</span><div><b>${alert.title}</b><small>${alert.detail}</small></div><time>${alert.time}</time></div>`).join("")}</div></article>
    </section><div class="spacer"></div>
    <section class="grid cols-3">
      <article class="panel"><div class="panel-heading"><div><h2>Market pulse</h2><p>Major benchmarks and breadth</p></div></div><div class="panel-body"><div class="allocation-row"><span>S&P 500</span><div class="bar"><span style="width:72%"></span></div><b class="positive">+0.42%</b></div><div class="allocation-row"><span>Nasdaq 100</span><div class="bar blue"><span style="width:84%"></span></div><b class="positive">+0.71%</b></div><div class="allocation-row"><span>Equal weight</span><div class="bar gold"><span style="width:55%"></span></div><b class="positive">+0.18%</b></div><div class="callout"><strong>Constructive, selective</strong>61% of the Atlas universe is advancing. AI infrastructure leads while consumer growth lags.</div></div></article>
      <article class="panel"><div class="panel-heading"><div><h2>Upcoming catalysts</h2><p>Next seven days</p></div></div><div class="panel-body list"><div class="list-row"><span class="list-icon">${icon("calendar")}</span><div><b>NVDA earnings</b><small>Wednesday · After market close</small></div><span class="tag risk">High impact</span></div><div class="list-row"><span class="list-icon">${icon("presentation")}</span><div><b>MSFT investor event</b><small>Thursday · 10:00 AM PT</small></div><span class="tag">Event</span></div><div class="list-row"><span class="list-icon">${icon("landmark")}</span><div><b>US employment report</b><small>Friday · 5:30 AM PT</small></div><span class="tag risk">Macro</span></div></div></article>
      <article class="panel"><div class="panel-heading"><div><h2>Latest research</h2><p>New and updated Atlas work</p></div><button class="button" data-go="reports">Archive</button></div><div class="panel-body list">${reports.slice(0,3).map(report => `<div class="list-row"><span class="list-icon">${icon("file-text")}</span><div><b>${report.title}</b><small>${report.type} · ${report.read}</small></div></div>`).join("")}</div></article>
    </section>`;
  initializePage();
  drawPerformanceChart("performance-chart");
}

function renderDiscover() {
  pageContent.innerHTML = pageHeading("Opportunity workspace", "Discover", "Find, compare, and save the strongest ideas across the Atlas universe.", `<button class="button">${icon("bookmark")} Saved screens</button><button class="button primary">${icon("plus")} New watchlist</button>`)
    + `<section class="grid cols-4"><article class="panel metric"><small>Covered securities</small><strong>117</strong><span>8 sectors · 11 themes</span></article><article class="panel metric"><small>Buy candidates</small><strong>6</strong><span class="positive">2 newly qualified</span></article><article class="panel metric"><small>Near buy range</small><strong>11</strong><span>Within 5% of target</span></article><article class="panel metric"><small>Risk reviews</small><strong>4</strong><span class="negative">1 high priority</span></article></section><div class="spacer"></div>
    <section class="panel table-panel"><div class="tabs"><button class="active">Rankings</button><button>Screener</button><button>Watchlists</button><button>Sectors & themes</button><button>Compare</button></div><div class="filter-bar"><select><option>All actions</option><option>Buy</option><option>Watch</option><option>Trim / Exit</option></select><select><option>All sectors</option><option>Semiconductors</option><option>Software</option><option>Cybersecurity</option><option>Defense</option></select><select><option>Atlas Score: 70+</option><option>80+</option><option>90+</option></select><select><option>Any position state</option><option>Not owned</option><option>Current holdings</option></select><button class="button">${icon("sliders-horizontal")} More filters</button><span class="filter-count">8 results</span></div>
    <table class="data-table"><thead><tr><th>Rank / Security</th><th>Action</th><th>Score</th><th>Price</th><th>Today</th><th>Conviction</th><th>Catalyst</th><th>Key risk</th><th></th></tr></thead><tbody>${securities.map((item,index) => `<tr><td><div style="display:flex;align-items:center;gap:12px"><b>${index+1}</b>${tickerCell(item)}</div></td><td><span class="tag ${actionClass(item.action)}">${item.action}</span></td><td><span class="score">${item.score}</span></td><td>$${item.price.toFixed(2)}</td><td class="${item.move>=0?"positive":"negative"}">${signed(item.move)}</td><td>${item.conviction}</td><td>${item.catalyst}</td><td>${item.risk}</td><td><button class="icon-button" data-security="${item.ticker}" aria-label="Research ${item.ticker}">${icon("chevron-right")}</button></td></tr>`).join("")}</tbody></table></section>`;
  initializePage();
}

function researchTabs(item, activeTab) {
  const tabs = [["overview", "Overview"], ["financials", "Financials"], ["valuation", "Valuation"], ["news", "News & events"], ["peers", "Peers"], ["history", "Research history"]];
  return `<div class="tabs" role="tablist" aria-label="${item.ticker} research views">${tabs.map(([key, label]) => `<button role="tab" aria-selected="${key === activeTab}" class="${key === activeTab ? "active" : ""}" data-research-tab="${key}" data-ticker="${item.ticker}">${label}</button>`).join("")}</div>`;
}

function researchOverview(item) {
  const position = positionFor(item.ticker);
  const portfolio = portfolioSnapshot();
  const positionSummary = position
    ? `${position.shares} simulated shares · ${percent(position.marketValue / portfolio.totalValue * 100)} current weight · ${percent(item.targetWeight)} target`
    : `Not currently owned · proposed paper weight ${percent(item.targetWeight)}`;
  return `<section class="grid two-one"><article class="panel"><div class="panel-heading"><div><h2>Atlas investment thesis</h2><p>Current view and the evidence that could change it</p></div><span class="tag ${actionClass(item.action)}">${item.conviction} confidence</span></div><div class="panel-body"><h3 class="research-thesis">${item.thesisTitle}</h3><p class="research-copy">${item.thesis}</p><div class="grid cols-3"><div class="callout"><strong>Why now</strong>${item.whyNow}</div><div class="callout"><strong>Primary catalyst</strong>${item.catalyst}</div><div class="callout risk"><strong>Invalidation trigger</strong>${item.invalidation}</div></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Decision context</h2><p>How the view relates to this paper portfolio</p></div></div><div class="panel-body decision-context"><div><span>Atlas action</span><strong class="tag ${actionClass(item.action)}">${item.action}</strong></div><div><span>Position</span><strong>${positionSummary}</strong></div><div><span>Preferred range</span><strong>${item.preferredRange}</strong></div><div><span>Key risk</span><strong>${item.risk}</strong></div><button class="button primary" data-decision="${item.ticker}">${icon("clipboard-check")} Preview paper plan</button><small>Preview only. The static site cannot submit a paper or real order.</small></div></article></section><div class="spacer"></div>
    <section class="grid two-one"><article class="panel"><div class="panel-heading"><div><h2>Price context</h2><p>Illustrative one-year series through the sample close</p></div><div class="segment-control"><button disabled>1M</button><button disabled>3M</button><button class="active">1Y</button><button disabled>5Y</button></div></div><div class="chart-wrap"><canvas id="security-chart"></canvas><div class="chart-legend"><span><i class="legend-dot"></i>${item.ticker} +${item.return1y.toFixed(1)}%</span><span><i class="legend-dot spy"></i>SPY +16.2%</span></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Atlas Score</h2><p>0-100 composite · higher indicates stronger evidence</p></div></div><div class="panel-body score-breakdown"><div class="score-large"><strong>${item.score}</strong></div><div class="score-bars">${Object.entries(item.scores).map(([label, value]) => `<div class="allocation-row"><span>${label}</span><div class="bar ${label === "Risk" ? "gold" : ""}"><span style="width:${value}%"></span></div><b>${value}</b></div>`).join("")}</div></div><div class="score-note"><strong>How to read this</strong>Growth 40%, Quality 20%, Moat 15%, Momentum 15%, and Risk 10%. Risk is scored higher when the risk profile is stronger.</div></article></section>`;
}

function researchDetail(item, activeTab) {
  if (activeTab === "overview") return researchOverview(item);
  if (activeTab === "financials") return `<section class="grid two-one"><article class="panel"><div class="panel-heading"><div><h2>Forward growth profile</h2><p>Illustrative consensus estimates</p></div></div><div class="panel-body">${Object.entries(item.growth).map(([label, value], index) => `<div class="allocation-row"><span>${label}</span><div class="bar ${index === 1 ? "blue" : index === 2 ? "gold" : ""}"><span style="width:${Math.min(95, Math.max(20, parseFloat(value) * 2))}%"></span></div><b>${value}</b></div>`).join("")}</div></article><article class="panel"><div class="panel-heading"><div><h2>Financial interpretation</h2><p>What Atlas is looking for</p></div></div><div class="panel-body"><div class="callout"><strong>Current view</strong>${item.thesis}</div><div class="callout risk"><strong>Failure condition</strong>${item.invalidation}</div></div></article></section>`;
  if (activeTab === "valuation") return `<section class="grid two-one"><article class="panel"><div class="panel-heading"><div><h2>Valuation dashboard</h2><p>Forward measures versus history and peers</p></div></div><div class="panel-body list">${item.valuation.map(([label, value, context]) => `<div class="list-row"><div><b>${label}</b><small>${context}</small></div><b>${value}</b></div>`).join("")}</div></article><article class="panel"><div class="panel-heading"><div><h2>Entry discipline</h2><p>Price context for the current Atlas view</p></div></div><div class="panel-body decision-context"><div><span>Preferred range</span><strong>${item.preferredRange}</strong></div><div><span>Current sample price</span><strong>${money(item.price, 2)}</strong></div><div><span>Recommendation</span><strong>${item.action}</strong></div><div><span>Valuation risk</span><strong>${item.risk}</strong></div></div></article></section>`;
  if (activeTab === "news") return `<section class="grid two-one"><article class="panel"><div class="panel-heading"><div><h2>Latest evidence</h2><p>Illustrative news, estimates, and filing signals</p></div></div><div class="panel-body list">${item.evidence.map((evidence, index) => `<div class="list-row"><span class="list-icon">${icon(index === 0 ? "newspaper" : index === 1 ? "trending-up" : "file-check-2")}</span><div><b>${evidence}</b><small>Sample evidence · Aug ${28 - index}, 2026</small></div></div>`).join("")}</div></article><article class="panel"><div class="panel-heading"><div><h2>Upcoming review</h2><p>Catalysts and decision dates</p></div></div><div class="panel-body timeline"><div class="timeline-item"><b>${item.catalyst}</b><small>Primary catalyst · high relevance</small></div><div class="timeline-item"><b>Atlas thesis review</b><small>Sep 16 · refresh score, range, and position guidance</small></div></div></article></section>`;
  if (activeTab === "peers") {
    const peers = securities.filter(peer => peer.ticker !== item.ticker && (peer.sector === item.sector || peer.sector.includes("Software") || item.sector.includes("Software"))).slice(0, 4);
    return `<section class="panel table-panel"><div class="panel-heading"><div><h2>Comparable Atlas coverage</h2><p>Related companies in this prototype universe</p></div></div><table class="data-table"><thead><tr><th>Security</th><th>Sector</th><th>Atlas Score</th><th>Action</th><th>Sample price</th><th></th></tr></thead><tbody>${peers.map(peer => `<tr><td>${tickerCell(peer)}</td><td>${peer.sector}</td><td><span class="score">${peer.score}</span></td><td><span class="tag ${actionClass(peer.action)}">${peer.action}</span></td><td>${money(peer.price, 2)}</td><td><button class="icon-button" data-security="${peer.ticker}" aria-label="Research ${peer.ticker}">${icon("chevron-right")}</button></td></tr>`).join("")}</tbody></table></section>`;
  }
  return `<section class="panel"><div class="panel-heading"><div><h2>Research history</h2><p>Illustrative changes to the Atlas view</p></div></div><div class="panel-body timeline"><div class="timeline-item"><b>Current ${item.action.toLowerCase()} view confirmed</b><small>Aug 28 · Score ${item.score} · ${item.whyNow}</small></div><div class="timeline-item"><b>Evidence set refreshed</b><small>Aug 26 · New estimate and filing signals incorporated</small></div><div class="timeline-item"><b>Risk language reviewed</b><small>Aug 21 · ${item.risk}</small></div></div></section>`;
}

function renderResearch(ticker = "NVDA", activeTab = "overview") {
  const item = securities.find(row => row.ticker === ticker) || securities[0];
  pageContent.innerHTML = pageHeading("Company research", `${item.ticker} research`, "Evidence, valuation, catalysts, and risks behind the current Atlas view.", `<button class="button" data-watch="${item.ticker}">${icon("bookmark-plus")} Add to prototype watchlist</button>`)
    + `<section class="panel"><div class="research-header"><div class="security-title"><span class="ticker-logo">${item.ticker.slice(0, 2)}</span><div><h1>${item.name} <span class="tag ${actionClass(item.action)}">${item.action}</span></h1><p>${item.ticker} · ${item.sector} · ${item.exchange} · sample close</p></div></div><div class="quote"><strong>${money(item.price, 2)}</strong><span class="${item.move >= 0 ? "positive" : "negative"}">${signed(item.move)} at sample close</span></div></div>${researchTabs(item, activeTab)}</section><div class="spacer"></div>${researchDetail(item, activeTab)}`;
  initializePage();
  drawPerformanceChart("security-chart", true);
}

function decisionStepper(item, activeStep) {
  const steps = [["evidence", "Evidence"], ["impact", "Portfolio impact"], ["policy", "Policy checks"], ["confirm", "Confirmation"]];
  const activeIndex = steps.findIndex(([key]) => key === activeStep);
  return `<nav class="workflow-steps" aria-label="Paper decision preview progress">${steps.map(([key, label], index) => `<button class="workflow-step ${key === activeStep ? "active" : ""} ${index < activeIndex ? "complete" : ""}" ${key === "evidence" ? `data-security="${item.ticker}"` : `data-decision-step="${key}" data-ticker="${item.ticker}"`}><span>${index < activeIndex ? icon("check") : index + 1}</span><b>${label}</b></button>`).join("")}</nav>`;
}

function decisionStage(preview, activeStep) {
  const { item } = preview;
  if (activeStep === "policy") {
    return `<article class="panel decision-stage"><div class="panel-heading"><div><h2>Paper-policy checks</h2><p>What Atlas must validate again on the authorized server</p></div><span class="tag risk">1 server gate</span></div><div class="panel-body policy-checks">${preview.checks.map(check => `<div class="policy-check"><span class="list-icon ${check.blocked ? "warning" : check.passed ? "positive" : "negative"}">${icon(check.blocked ? "server-cog" : check.passed ? "check" : "x")}</span><div><b>${check.label}</b><small>${check.detail}</small></div><span class="tag ${check.blocked ? "risk" : check.passed ? "buy" : "sell"}">${check.blocked ? "Server required" : check.passed ? "Clear" : "Blocked"}</span></div>`).join("")}</div><div class="decision-footer"><button class="button" data-decision-step="impact" data-ticker="${item.ticker}">${icon("arrow-left")} Back</button><button class="button primary" data-decision-step="confirm" data-ticker="${item.ticker}">Review boundary ${icon("arrow-right")}</button></div></article>`;
  }
  if (activeStep === "confirm") {
    return `<article class="panel decision-stage"><div class="panel-heading"><div><h2>Confirmation boundary</h2><p>The design stops before any authorized account change</p></div><span class="tag risk">Locked</span></div><div class="panel-body"><div class="authority-boundary"><span class="boundary-icon">${icon("shield-alert")}</span><div><p class="eyebrow">No transaction will be created</p><h3>The static prototype cannot submit this paper decision.</h3><p>The production workflow must refresh prices, rerun risk checks, verify the signed-in owner and CSRF token, require the exact simulation confirmation, and append the result to the audit ledger.</p></div></div><div class="confirmation-actions"><button class="button" data-decision-step="policy" data-ticker="${item.ticker}">${icon("arrow-left")} Back to checks</button><button class="button" data-acknowledge-preview="${item.ticker}">${icon("check-circle-2")} Acknowledge preview only</button><button class="button primary" disabled title="Requires authorized Atlas server integration">Submit paper decision</button></div><p class="decision-note">Acknowledging saves only a temporary browser note so you can inspect the proposed Activity experience. It is not a paper fill, owner approval, or audit event.</p></div></article>`;
  }
  return `<article class="panel decision-stage"><div class="panel-heading"><div><h2>Projected paper impact</h2><p>Calculated from the illustrative account at the sample close</p></div><span class="tag ${actionClass(item.action)}">${item.action}</span></div><div class="panel-body"><div class="projection-summary"><span class="ticker-logo">${item.ticker.slice(0, 2)}</span><div><p class="eyebrow">Proposed instruction</p><h3>${preview.instruction}</h3><p>${preview.actionable ? `Estimated at ${money(item.price, 2)} per share before simulated costs.` : "The current recommendation calls for monitoring rather than a transaction."}</p></div></div><div class="projection-grid"><div><span>Position value</span><strong>${money(preview.currentValue)} → ${money(preview.projectedPositionValue)}</strong></div><div><span>Portfolio weight</span><strong>${percent(preview.currentWeight)} → ${percent(preview.projectedWeight)}</strong></div><div><span>Available cash</span><strong>${money(paperAccount.cash)} → ${money(preview.projectedCash)}</strong></div><div><span>Cash reserve</span><strong>${percent(preview.portfolio.cashWeight)} → ${percent(preview.projectedCashWeight)}</strong></div></div><div class="callout"><strong>Why Atlas proposed this</strong>${item.whyNow}</div><div class="callout risk"><strong>What would invalidate it</strong>${item.invalidation}</div></div><div class="decision-footer"><button class="button" data-security="${item.ticker}">${icon("arrow-left")} Back to evidence</button><button class="button primary" data-decision-step="policy" data-ticker="${item.ticker}" ${preview.actionable ? "" : "disabled"}>Check paper policy ${icon("arrow-right")}</button></div></article>`;
}

function renderDecision(ticker = "NVDA", activeStep = "impact") {
  const item = securities.find(row => row.ticker === ticker) || securities[0];
  if (activeStep === "evidence") {
    location.hash = researchUrl(item.ticker);
    return;
  }
  const allowedSteps = new Set(["impact", "policy", "confirm"]);
  const step = allowedSteps.has(activeStep) ? activeStep : "impact";
  const preview = decisionPreview(item);
  pageContent.innerHTML = pageHeading("Paper decision workflow", `${item.ticker} decision preview`, "Understand the proposed action and its portfolio effect before any authorized submission.", `<button class="button" data-security="${item.ticker}">${icon("file-search")} Research evidence</button>`)
    + decisionStepper(item, step)
    + `<section class="grid two-one">${decisionStage(preview, step)}<aside class="panel order-ticket"><div class="panel-heading"><div><h2>Preview ticket</h2><p>Illustrative estimate only</p></div></div><div class="panel-body decision-context"><div><span>Account</span><strong>Atlas Paper Portfolio</strong></div><div><span>Instruction</span><strong>${preview.instruction}</strong></div><div><span>Estimated value</span><strong>${money(preview.estimatedValue)}</strong></div><div><span>Sample price</span><strong>${money(item.price, 2)}</strong></div><div><span>Target weight</span><strong>${percent(item.targetWeight)}</strong></div><div><span>Authority</span><strong class="tag risk">Preview only</strong></div><small>No broker is connected. No paper ledger write occurs from this prototype.</small></div></aside></section>`;
  initializePage();
}

function renderPortfolio() {
  const portfolio = portfolioSnapshot();
  const totalReturn = (portfolio.totalValue / paperAccount.startingValue - 1) * 100;
  const unrealizedReturn = portfolio.unrealized / portfolio.costBasis * 100;
  const allocations = portfolio.positions.reduce((groups, position) => {
    groups[position.security.sector] = (groups[position.security.sector] || 0) + position.marketValue;
    return groups;
  }, {});
  const allocationRows = [["Cash", paperAccount.cash, "gold"], ...Object.entries(allocations).map(([label, value], index) => [label, value, index === 1 ? "blue" : index === 3 ? "red" : ""])];
  pageContent.innerHTML = pageHeading("Paper account", "Portfolio", "Performance, positions, allocation, and risk for the simulated Atlas portfolio.", `<select class="button"><option>Atlas Paper Portfolio</option></select><button class="button">${icon("download")} Export</button><button class="button primary">${icon("wand-sparkles")} Review rebalance</button>`)
    + `<section class="grid cols-4"><article class="panel metric"><small>Total value</small><strong>${money(portfolio.totalValue)}</strong><span class="${totalReturn >= 0 ? "positive" : "negative"}">${signed(totalReturn)} since start</span></article><article class="panel metric"><small>Invested</small><strong>${money(portfolio.invested)}</strong><span>${percent(portfolio.invested / portfolio.totalValue * 100)} exposure</span></article><article class="panel metric"><small>Unrealized gain</small><strong>${money(portfolio.unrealized)}</strong><span class="${portfolio.unrealized >= 0 ? "positive" : "negative"}">${signed(unrealizedReturn)}</span></article><article class="panel metric"><small>Risk level</small><strong>Moderate</strong><span class="warning">2 positions need review</span></article></section><div class="spacer"></div>
    <section class="grid two-one"><article class="panel"><div class="panel-heading"><div><h2>Performance</h2><p>Atlas paper portfolio versus SPY (S&amp;P 500) and QQQ (Nasdaq-100)</p></div><div class="segment-control"><button disabled>1M</button><button class="active">3M</button><button disabled>1Y</button><button disabled>All</button></div></div><div class="chart-wrap"><canvas id="portfolio-chart"></canvas><div class="chart-legend"><span><i class="legend-dot"></i>Atlas ${signed(totalReturn)}</span><span><i class="legend-dot spy"></i>SPY +6.08%</span><span><i class="legend-dot qqq"></i>QQQ +5.44%</span></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Allocation</h2><p>Calculated from every simulated position and cash</p></div></div><div class="panel-body">${allocationRows.map(([label, value, color]) => { const weight = value / portfolio.totalValue * 100; return `<div class="allocation-row"><span>${label}</span><div class="bar ${color}"><span style="width:${weight}%"></span></div><b>${percent(weight)}</b></div>`; }).join("")}<div class="callout risk"><strong>Review queue</strong>AMZN is above target and META has an exit recommendation.</div></div></article></section><div class="spacer"></div>
    <section class="panel table-panel holdings-panel"><div class="panel-heading"><div><h2>Current simulated holdings</h2><p>${portfolio.positions.length} positions · values reconcile to ${money(portfolio.invested)} invested</p></div><span class="tag">Paper only</span></div><table class="data-table"><thead><tr><th>Holding</th><th>Atlas view</th><th>Shares</th><th>Sample price</th><th>Market value</th><th>Weight</th><th>Total return</th><th>Last session</th><th>Next action</th></tr></thead><tbody>${portfolio.positions.sort((a, b) => b.marketValue - a.marketValue).map(position => { const item = position.security; const holdingReturn = position.unrealized / position.costBasis * 100; return `<tr><td data-label="Holding">${tickerCell(item)}</td><td data-label="Atlas view"><span class="tag ${actionClass(item.action)}">${item.action}</span></td><td data-label="Shares">${position.shares}</td><td data-label="Sample price">${money(item.price, 2)}</td><td data-label="Market value">${money(position.marketValue)}</td><td data-label="Weight">${percent(position.marketValue / portfolio.totalValue * 100)}</td><td data-label="Total return" class="${holdingReturn >= 0 ? "positive" : "negative"}">${signed(holdingReturn)}</td><td data-label="Last session" class="${item.move >= 0 ? "positive" : "negative"}">${signed(item.move)}</td><td data-label="Next action">${item.action === "Trim" ? `Reduce toward ${percent(item.targetWeight)}` : item.action === "Exit" ? "Review paper exit" : "Monitor"}</td></tr>`; }).join("")}</tbody></table></section><div class="spacer"></div>
    <section class="grid cols-3"><article class="panel"><div class="panel-heading"><div><h2>Risk summary</h2><p>Portfolio-level exposure checks</p></div></div><div class="panel-body list"><div class="list-row"><span class="list-icon warning">${icon("layers-3")}</span><div><b>Position concentration</b><small>META is ${percent(positionFor("META").marketValue / portfolio.totalValue * 100)} of the paper portfolio and has an exit view.</small></div><span class="tag risk">Review</span></div><div class="list-row"><span class="list-icon positive">${icon("shield-check")}</span><div><b>Cash reserve</b><small>${percent(portfolio.cashWeight)} is above the 20% minimum.</small></div><span class="tag buy">Clear</span></div><div class="list-row"><span class="list-icon positive">${icon("waves")}</span><div><b>Drawdown</b><small>-3.8% versus -10% limit.</small></div><span class="tag buy">Clear</span></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Return attribution</h2><p>Largest contributors and detractors</p></div></div><div class="panel-body"><div class="allocation-row"><span>MSFT</span><div class="bar"><span style="width:82%"></span></div><b>+1.42%</b></div><div class="allocation-row"><span>PLTR</span><div class="bar"><span style="width:56%"></span></div><b>+0.88%</b></div><div class="allocation-row"><span>AMZN</span><div class="bar red"><span style="width:28%"></span></div><b>-0.31%</b></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Scenario check</h2><p>Estimated portfolio sensitivity</p></div></div><div class="panel-body"><div class="list"><div class="list-row"><div><b>Nasdaq -10%</b><small>Growth shock estimate</small></div><b class="negative">-7.4%</b></div><div class="list-row"><div><b>Rates +1%</b><small>Duration sensitivity</small></div><b class="negative">-3.1%</b></div><div class="list-row"><div><b>Defense +10%</b><small>Sector upside estimate</small></div><b class="positive">+1.2%</b></div></div></div></article></section>`;
  initializePage();
  drawPerformanceChart("portfolio-chart");
}

function renderActivity() {
  let previewReview = null;
  try { previewReview = JSON.parse(sessionStorage.getItem("atlasPreviewReview") || "null"); } catch { previewReview = null; }
  const previewNotice = previewReview ? `<section class="preview-activity"><span class="list-icon neutral">${icon("clipboard-check")}</span><div><p class="eyebrow">Browser-only preview</p><h2>${previewReview.ticker} paper plan reviewed</h2><p>${previewReview.instruction}. This temporary note demonstrates the Activity flow; no paper transaction, owner approval, or audit record was created.</p></div><button class="button" data-decision="${previewReview.ticker}">Reopen preview</button></section><div class="spacer"></div>` : "";
  pageContent.innerHTML = pageHeading("Decision history", "Activity", "A complete record of Atlas recommendations, owner decisions, and simulated transactions.", `<button class="button">${icon("sliders-horizontal")} Filter</button><button class="button">${icon("download")} Export audit log</button>`)
    + previewNotice
    + `<section class="grid cols-4"><article class="panel metric"><small>Recommendations</small><strong>67</strong><span>Current policy period</span></article><article class="panel metric"><small>Simulated buys</small><strong>21</strong><span class="positive">57% judged working</span></article><article class="panel metric"><small>Simulated sells</small><strong>14</strong><span class="positive">+0.8% avg decision edge</span></article><article class="panel metric"><small>Open decisions</small><strong>2</strong><span class="warning">Owner review requested</span></article></section><div class="spacer"></div>
    <section class="panel"><div class="tabs"><button class="active">All activity</button><button>Recommendations</button><button>Transactions</button><button>Owner decisions</button><button>Policy changes</button></div><div class="filter-bar"><select><option>Last 30 days</option><option>Last 90 days</option><option>All history</option></select><input type="search" placeholder="Filter by ticker"><span class="filter-count">12 recent events</span></div><div class="panel-body timeline">
      <div class="timeline-item"><b>Atlas recommended a simulated NVDA purchase</b><small>Today, 7:05 AM · 5.0% target weight · Score 94 · Awaiting entry condition</small></div>
      <div class="timeline-item"><b>AMZN trim review opened</b><small>Today, 7:05 AM · Position exceeded its target and relative strength weakened</small></div>
      <div class="timeline-item"><b>Simulated AVGO purchase recorded</b><small>Aug 28, 7:06 AM · 42 shares at $292.10 average cost · Automatic paper mode</small></div>
      <div class="timeline-item"><b>META exit recommendation created</b><small>Aug 28, 7:05 AM · Trend and estimate confirmation deteriorated</small></div>
      <div class="timeline-item"><b>Weekly strategy review completed</b><small>Aug 23, 8:04 AM · No policy settings changed</small></div>
      <div class="timeline-item"><b>Entry experiment result retained by owner</b><small>Aug 14, 3:18 PM · Typed owner confirmation · Paper policy only</small></div>
    </div></section>`;
  initializePage();
}

function renderReports() {
  const portfolio = portfolioSnapshot();
  const totalReturn = (portfolio.totalValue / paperAccount.startingValue - 1) * 100;
  const dayReturn = portfolio.dayChange / (portfolio.totalValue - portfolio.dayChange) * 100;
  const benchmarkEdge = totalReturn - 6.08;
  pageContent.innerHTML = pageHeading("Research library", "Reports", "Read, search, download, and share Atlas research products.", `<button class="button">${icon("search")} Search reports</button><button class="button primary">${icon("mail")} Email latest brief</button>`)
    + `<section class="panel report-layout"><aside class="report-list">${reports.map((report,index) => `<button class="report-item ${index===0?"active":""}" data-report="${index}"><span class="tag ${report.type.includes("Risk")?"risk":""}">${report.type}</span><b>${report.title}</b><small>${report.date} · ${report.read}</small></button>`).join("")}</aside><article class="report-reader"><p class="eyebrow">Sample Morning Executive Brief · August 29, 2026</p><h2>AI leadership broadens as market breadth improves</h2><div class="callout"><strong>Executive view</strong>The sample market remains constructive but selective. Atlas favors high-quality AI infrastructure while preserving cash for volatility around the next earnings and employment releases.</div><h3>What changed</h3><p>Sample market breadth improved to 61% across the Atlas universe. The calculated paper portfolio moved ${signed(dayReturn)} at the sample close, with consumer and communication holdings creating the largest drag.</p><h3>Recommended actions</h3><ul><li><strong>Buy candidate:</strong> NVIDIA entered the preferred range with a 94 Atlas Score and strong confirmation.</li><li><strong>Trim review:</strong> Amazon is ${percent(positionFor("AMZN").marketValue / portfolio.totalValue * 100)} of the portfolio versus a 6% target.</li><li><strong>Exit review:</strong> Meta breached the current paper risk threshold after a third weak observation.</li></ul><h3>Portfolio context</h3><p>The paper portfolio is worth ${money(portfolio.totalValue)} and has returned ${signed(totalReturn)} since its ${money(paperAccount.startingValue)} starting value. It is ${Math.abs(benchmarkEdge).toFixed(2)} percentage points ${benchmarkEdge >= 0 ? "ahead of" : "behind"} SPY. Cash is ${percent(portfolio.cashWeight)}, leaving room for a measured new position.</p><h3>Risks to watch</h3><p>NVIDIA earnings and the US employment report could increase volatility. Atlas will not change policy or expand position limits based on a single event.</p><p><small>Illustrative prototype content. Not investment advice and not a live order.</small></p></article></section>`;
  initializePage();
}

function renderAlerts() {
  pageContent.innerHTML = pageHeading("Attention center", "Alerts", "Review material changes and control how Atlas reaches you.", `<button class="button">${icon("check-check")} Mark all read</button><button class="button primary">${icon("plus")} New alert rule</button>`)
    + `<section class="grid one-two"><aside class="panel"><div class="panel-heading"><div><h2>Alert rules</h2><p>Enabled notification categories</p></div></div><div class="panel-body"><div class="toggle-row"><div><b>Recommendation changes</b><small>Buy, trim, and exit updates</small></div><button class="switch on" aria-label="Toggle recommendation alerts"></button></div><div class="toggle-row"><div><b>Portfolio risk</b><small>Limits, concentration, and drawdown</small></div><button class="switch on" aria-label="Toggle risk alerts"></button></div><div class="toggle-row"><div><b>Earnings and events</b><small>Upcoming catalysts and results</small></div><button class="switch on" aria-label="Toggle event alerts"></button></div><div class="toggle-row"><div><b>News and analyst actions</b><small>Material changes only</small></div><button class="switch" aria-label="Toggle news alerts"></button></div><div class="toggle-row"><div><b>Daily report delivery</b><small>Email at 7:15 AM PT</small></div><button class="switch on" aria-label="Toggle report delivery"></button></div></div></aside><section class="panel"><div class="tabs"><button class="active">Inbox <span class="tag risk">3 new</span></button><button>High priority</button><button>History</button></div><div class="panel-body list">${[...alerts,{severity:"Low",title:"Weekly report is ready",detail:"The latest portfolio and strategy review is available.",time:"Aug 23",icon:"notebook-text"},{severity:"Low",title:"MSFT score increased from 89 to 91",detail:"Growth and momentum components improved after new estimate revisions.",time:"Aug 22",icon:"arrow-up-right"}].map(alert => `<div class="list-row"><span class="list-icon ${alert.severity==="High"?"negative":alert.severity==="Medium"?"warning":"neutral"}">${icon(alert.icon)}</span><div><b>${alert.title}</b><small>${alert.detail}</small></div><time>${alert.time}</time></div>`).join("")}</div></section></section>`;
  initializePage();
}

function renderSettings() {
  pageContent.innerHTML = pageHeading("Owner workspace", "Settings", "Manage your account, investment preferences, security, and Atlas operating mode.", `<button class="button primary">Save changes</button>`)
    + `<section class="grid one-two"><aside class="panel"><div class="panel-body list"><button class="report-item active">Profile & workspace</button><button class="report-item">Investment preferences</button><button class="report-item">Paper portfolio</button><button class="report-item">Notifications</button><button class="report-item">Security & sessions</button><button class="report-item">Data & privacy</button><button class="report-item">Integrations</button><button class="report-item">Subscription</button></div></aside><section class="panel"><div class="panel-heading"><div><h2>Profile and workspace</h2><p>Your private Atlas account details</p></div></div><div class="panel-body"><div class="toggle-row"><div><b>Workspace name</b><small>Atlas Owner Workspace</small></div><button class="button">Edit</button></div><div class="toggle-row"><div><b>Account email</b><small>jlukacsffi@gmail.com · verified</small></div><span class="tag buy">Verified</span></div><div class="toggle-row"><div><b>Operating mode</b><small>Atlas may create and execute simulated paper decisions under current policy.</small></div><div class="segment-control"><button>Recommend</button><button class="active">Paper auto</button><button disabled>Live</button></div></div><div class="toggle-row"><div><b>Real-money brokerage</b><small>No broker is connected. Live execution requires a separate approved stage.</small></div><span class="tag risk">Disabled</span></div><div class="toggle-row"><div><b>Time zone</b><small>America/Los_Angeles</small></div><button class="button">Change</button></div><div class="toggle-row"><div><b>Currency</b><small>US Dollar (USD)</small></div><button class="button">Change</button></div><div class="toggle-row"><div><b>Multi-factor authentication</b><small>Google account protection is active.</small></div><span class="tag buy">Protected</span></div></div></section></section><div class="spacer"></div><section class="panel"><div class="panel-heading"><div><h2>Future integrations</h2><p>These capabilities remain disabled until their security and authority stages are approved.</p></div></div><div class="panel-body grid cols-3"><div class="callout"><strong>Read-only brokerage sync</strong>Import balances and holdings without order authority. Not connected.</div><div class="callout"><strong>Tax platform export</strong>Export lots and realized activity for review. Planned.</div><div class="callout risk"><strong>Live trade execution</strong>Locked pending evidence, legal, security, and explicit owner approval.</div></div></section>`;
  initializePage();
}

function initializePage() {
  if (window.lucide) lucide.createIcons();
  pageContent.querySelectorAll("[data-go]").forEach(button => button.addEventListener("click", () => { location.hash = button.dataset.go; }));
  pageContent.querySelectorAll("[data-security]").forEach(button => button.addEventListener("click", () => { location.hash = researchUrl(button.dataset.security); }));
  pageContent.querySelectorAll("[data-decision]").forEach(button => button.addEventListener("click", () => { location.hash = decisionUrl(button.dataset.decision); }));
  pageContent.querySelectorAll("[data-decision-step]").forEach(button => button.addEventListener("click", () => { location.hash = decisionUrl(button.dataset.ticker, button.dataset.decisionStep); }));
  pageContent.querySelectorAll("[data-acknowledge-preview]").forEach(button => button.addEventListener("click", () => {
    const item = securities.find(row => row.ticker === button.dataset.acknowledgePreview) || securities[0];
    const preview = decisionPreview(item);
    sessionStorage.setItem("atlasPreviewReview", JSON.stringify({ ticker: item.ticker, instruction: preview.instruction }));
    location.hash = "activity";
  }));
  pageContent.querySelectorAll("[data-research-tab]").forEach(button => button.addEventListener("click", () => { location.hash = researchUrl(button.dataset.ticker, button.dataset.researchTab); }));
  pageContent.querySelectorAll("[data-watch]").forEach(button => button.addEventListener("click", () => showToast(`${button.dataset.watch} added to your prototype watchlist.`)));
  pageContent.querySelectorAll(".segment-control button:not([disabled])").forEach(button => button.addEventListener("click", () => { button.parentElement.querySelectorAll("button").forEach(item => item.classList.remove("active")); button.classList.add("active"); showToast(`View changed to ${button.textContent.trim()}.`); }));
  pageContent.querySelectorAll(".tabs button:not([data-research-tab])").forEach(button => button.addEventListener("click", () => { button.parentElement.querySelectorAll("button").forEach(item => item.classList.remove("active")); button.classList.add("active"); showToast(`${button.textContent.trim()} is shown as a planned prototype view.`); }));
  pageContent.querySelectorAll(".switch").forEach(button => {
    button.setAttribute("role", "switch");
    button.setAttribute("aria-checked", button.classList.contains("on"));
    button.addEventListener("click", () => {
      button.classList.toggle("on");
      button.setAttribute("aria-checked", button.classList.contains("on"));
      showToast("Prototype preference changed for this preview only.");
    });
  });
}

function drawPerformanceChart(id, security = false) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 700;
  const height = canvas.clientHeight || 220;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const styles = getComputedStyle(document.documentElement);
  const line = styles.getPropertyValue("--line").trim();
  ctx.strokeStyle = line;
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i += 1) {
    const y = 12 + i * ((height - 30) / 4);
    ctx.beginPath(); ctx.moveTo(10, y); ctx.lineTo(width - 10, y); ctx.stroke();
  }
  const series = security ? [
    { color: "#586fdb", data: [20,22,21,28,31,36,34,41,48,52,59,64] },
    { color: "#3984c6", data: [20,21,22,23,26,27,29,31,33,34,36,38] }
  ] : [
    { color: "#586fdb", data: [30,31,29,34,36,35,39,42,43,47,46,51] },
    { color: "#3984c6", data: [30,32,31,35,38,39,42,44,46,49,50,54] },
    { color: "#e08a52", data: [30,31,30,34,37,38,40,43,44,47,48,52] }
  ];
  series.forEach(item => {
    ctx.strokeStyle = item.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    item.data.forEach((value,index) => {
      const x = 12 + index * ((width - 24) / (item.data.length - 1));
      const y = height - 15 - (value - 15) * ((height - 35) / 55);
      if (index === 0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    });
    ctx.stroke();
  });
}

function route() {
  const [name = "today", ticker = "NVDA", activeTab = "overview"] = (location.hash.replace("#", "") || "today").split("/");
  const activeNavigation = name === "decision" ? "research" : name;
  document.querySelectorAll(".nav-link").forEach(link => link.classList.toggle("active", link.dataset.route === activeNavigation));
  document.querySelector(".sidebar").classList.remove("open");
  const routes = {
    today: renderToday,
    discover: renderDiscover,
    research: () => renderResearch(ticker.toUpperCase(), activeTab),
    decision: () => renderDecision(ticker.toUpperCase(), activeTab),
    portfolio: renderPortfolio,
    activity: renderActivity,
    reports: renderReports,
    alerts: renderAlerts,
    settings: renderSettings
  };
  (routes[name] || renderToday)();
  window.scrollTo(0,0);
}

searchInput.addEventListener("input", () => {
  const query = searchInput.value.trim().toLowerCase();
  if (!query) { searchResults.hidden = true; return; }
  const matches = securities.filter(item => `${item.ticker} ${item.name} ${item.sector}`.toLowerCase().includes(query)).slice(0,5);
  searchResults.innerHTML = matches.length ? matches.map(item => `<button class="search-result" data-search-ticker="${item.ticker}"><b>${item.ticker}</b><small>${item.name} · ${item.sector}</small><span>Score ${item.score}</span></button>`).join("") : `<div class="empty-state"><div><h3>No matching securities</h3><p>Try a ticker, company, sector, or theme.</p></div></div>`;
  searchResults.hidden = false;
  searchResults.querySelectorAll("[data-search-ticker]").forEach(button => button.addEventListener("click", () => { searchResults.hidden = true; searchInput.value = ""; location.hash = researchUrl(button.dataset.searchTicker); }));
});

document.addEventListener("keydown", event => {
  if (event.key === "/" && document.activeElement !== searchInput) { event.preventDefault(); searchInput.focus(); }
  if (event.key === "Escape") { searchResults.hidden = true; searchInput.blur(); }
});
document.getElementById("mobile-menu").addEventListener("click", () => document.querySelector(".sidebar").classList.toggle("open"));
document.querySelectorAll("[data-go]").forEach(button => button.addEventListener("click", () => { location.hash = button.dataset.go; }));
window.addEventListener("hashchange", route);
window.addEventListener("resize", () => { const chart = document.querySelector("canvas"); if (chart) route(); });
route();
