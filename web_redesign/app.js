const securities = [
  { ticker: "NVDA", name: "NVIDIA", sector: "Semiconductors", score: 94, price: 182.74, move: 2.8, action: "Buy", conviction: "High", catalyst: "Blackwell demand", risk: "Premium valuation", owned: false },
  { ticker: "MSFT", name: "Microsoft", sector: "Software", score: 91, price: 536.12, move: 0.9, action: "Buy", conviction: "High", catalyst: "Azure AI growth", risk: "AI capex intensity", owned: true },
  { ticker: "AVGO", name: "Broadcom", sector: "Semiconductors", score: 89, price: 316.84, move: 1.7, action: "Watch", conviction: "Medium", catalyst: "Custom accelerator demand", risk: "Integration execution", owned: true },
  { ticker: "CRWD", name: "CrowdStrike", sector: "Cybersecurity", score: 87, price: 471.36, move: -0.6, action: "Watch", conviction: "Medium", catalyst: "Platform consolidation", risk: "Multiple compression", owned: false },
  { ticker: "PLTR", name: "Palantir", sector: "Software", score: 85, price: 152.20, move: 3.1, action: "Hold", conviction: "Medium", catalyst: "Commercial acceleration", risk: "Valuation concentration", owned: true },
  { ticker: "LMT", name: "Lockheed Martin", sector: "Aerospace & Defense", score: 82, price: 498.18, move: -1.2, action: "Hold", conviction: "Medium", catalyst: "Backlog conversion", risk: "Program timing", owned: true },
  { ticker: "AMZN", name: "Amazon", sector: "Consumer & Cloud", score: 80, price: 229.41, move: -2.4, action: "Trim", conviction: "Medium", catalyst: "AWS reacceleration", risk: "Margin normalization", owned: true },
  { ticker: "META", name: "Meta Platforms", sector: "Communication", score: 74, price: 681.32, move: -3.6, action: "Exit", conviction: "High", catalyst: "Ad efficiency", risk: "Capital spending", owned: true }
];

const alerts = [
  { severity: "High", title: "META breached Atlas risk threshold", detail: "Relative strength and estimate momentum weakened for a third observation.", time: "18 min ago", icon: "triangle-alert" },
  { severity: "Medium", title: "NVDA entered the buy range", detail: "Price is within 1.8% of Atlas's preferred entry zone with strong confirmation.", time: "42 min ago", icon: "circle-dollar-sign" },
  { severity: "Medium", title: "AMZN position exceeds target weight", detail: "The simulated position is 1.4 percentage points above its 6% target.", time: "2 hr ago", icon: "scale" }
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
const actionClass = (action) => action === "Buy" ? "buy" : action === "Exit" || action === "Trim" ? "sell" : "watch";
const pageHeading = (eyebrow, title, detail, actions = "") => `
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
  pageContent.innerHTML = pageHeading("Saturday, August 29", "Good morning, Joe", "Your portfolio, recommendations, and risks in one decision view.", `
    <button class="button">${icon("calendar-days")} Upcoming events</button><button class="button primary" data-go="reports">${icon("notebook-text")} Morning brief</button>`)
    + `<section class="panel decision-brief">
      <div class="brief-main"><span class="tag buy">Primary recommendation</span><h2>Add NVIDIA to the paper portfolio near the preferred entry range.</h2><p>Atlas sees durable AI infrastructure demand, improving sector breadth, and strong relative momentum. Position sizing remains limited because valuation is elevated.</p><div class="brief-actions"><button class="button primary" data-security="NVDA">Review NVDA</button><button class="button" data-watch="NVDA">Add to watchlist</button></div></div>
      <div class="brief-side"><div><span>Atlas Score</span><strong>94 / 100</strong></div><div><span>Conviction</span><strong>High</strong></div><div><span>Preferred range</span><strong>$176–$184</strong></div><div><span>Suggested paper weight</span><strong>5.0%</strong></div><div><span>Key risk</span><strong>Premium valuation</strong></div></div>
    </section><div class="spacer"></div>
    <section class="grid cols-4">
      <article class="panel metric"><small>Paper portfolio</small><strong>$104,820</strong><span class="positive">+4.82% all time</span></article>
      <article class="panel metric"><small>Today</small><strong>+$612</strong><span class="positive">+0.59%</span></article>
      <article class="panel metric"><small>Available cash</small><strong>$31,460</strong><span>30.0% of portfolio</span></article>
      <article class="panel metric"><small>Benchmark edge</small><strong>-1.26%</strong><span class="negative">Behind SPY since start</span></article>
    </section><div class="spacer"></div>
    ${recommendationsTable(securities.slice(0, 5))}<div class="spacer"></div>
    <section class="grid two-one">
      <article class="panel"><div class="panel-heading"><div><h2>Portfolio performance</h2><p>Atlas paper portfolio versus broad-market benchmarks</p></div><div class="segment-control"><button class="active" data-period="1M">1M</button><button data-period="3M">3M</button><button data-period="1Y">1Y</button><button data-period="ALL">All</button></div></div><div class="chart-wrap"><canvas id="performance-chart"></canvas><div class="chart-legend"><span><i class="legend-dot"></i>Atlas +4.82%</span><span><i class="legend-dot spy"></i>SPY +6.08%</span><span><i class="legend-dot qqq"></i>QQQ +5.44%</span></div></div></article>
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

function renderResearch(ticker = "NVDA") {
  const item = securities.find(row => row.ticker === ticker) || securities[0];
  pageContent.innerHTML = pageHeading("Company research", "Research", "Evidence, valuation, catalysts, and risks behind every Atlas view.", `<button class="button" data-watch="${item.ticker}">${icon("bookmark-plus")} Add to watchlist</button><button class="button primary">${icon("git-compare-arrows")} Compare</button>`)
    + `<section class="panel"><div class="research-header"><div class="security-title"><span class="ticker-logo">${item.ticker.slice(0,2)}</span><div><h1>${item.name} <span class="tag ${actionClass(item.action)}">${item.action}</span></h1><p>${item.ticker} · ${item.sector} · NASDAQ · Data delayed 15 minutes</p></div></div><div class="quote"><strong>$${item.price.toFixed(2)}</strong><span class="${item.move>=0?"positive":"negative"}">${signed(item.move)} today</span></div></div><div class="tabs"><button class="active">Overview</button><button>Financials</button><button>Valuation</button><button>News & events</button><button>Peers</button><button>Research history</button></div></section><div class="spacer"></div>
    <section class="grid two-one"><article class="panel"><div class="panel-heading"><div><h2>Atlas investment thesis</h2><p>Current view and the evidence that could change it</p></div><span class="tag buy">High conviction</span></div><div class="panel-body"><h3 style="font-size:16px;margin:0 0 8px">AI infrastructure leadership remains durable.</h3><p style="color:var(--muted);font-size:11px;line-height:1.65">NVIDIA combines exceptional growth, category leadership, expanding software economics, and strong balance-sheet quality. The current setup is supported by improving semiconductor breadth and persistent estimate revisions.</p><div class="grid cols-3"><div class="callout"><strong>Why now</strong>Price has returned to the preferred entry range while confirmation remains constructive.</div><div class="callout"><strong>Primary catalyst</strong>Blackwell revenue ramp and raised data-center demand expectations.</div><div class="callout risk"><strong>What could break</strong>Hyperscaler capex slowdown or gross-margin compression.</div></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Atlas Score</h2><p>Weighted fundamental and market evidence</p></div></div><div class="panel-body score-breakdown"><div class="score-large"><strong>${item.score}</strong></div><div class="score-bars">${[["Growth",97],["Quality",93],["Moat",96],["Momentum",89],["Risk",76]].map(([label,value]) => `<div class="allocation-row"><span>${label}</span><div class="bar ${label==="Risk"?"gold":""}"><span style="width:${value}%"></span></div><b>${value}</b></div>`).join("")}</div></div></article></section><div class="spacer"></div>
    <section class="grid two-one"><article class="panel"><div class="panel-heading"><div><h2>Price and events</h2><p>One year · split adjusted · key Atlas events</p></div><div class="segment-control"><button>1M</button><button>3M</button><button class="active">1Y</button><button>5Y</button></div></div><div class="chart-wrap"><canvas id="security-chart"></canvas><div class="chart-legend"><span><i class="legend-dot"></i>${item.ticker} +34.7%</span><span><i class="legend-dot spy"></i>SPY +16.2%</span></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Upcoming events</h2><p>Catalysts and decision dates</p></div></div><div class="panel-body timeline"><div class="timeline-item"><b>Q2 earnings release</b><small>Sep 2 · Consensus revenue $46.1B · High impact</small></div><div class="timeline-item"><b>Technology conference</b><small>Sep 11 · Management presentation</small></div><div class="timeline-item"><b>Atlas thesis review</b><small>Sep 16 · Reassess score, entry range, and position size</small></div></div></article></section><div class="spacer"></div>
    <section class="grid cols-3"><article class="panel"><div class="panel-heading"><div><h2>Growth trend</h2><p>Forward estimates</p></div></div><div class="panel-body"><div class="allocation-row"><span>Revenue</span><div class="bar"><span style="width:88%"></span></div><b>+42%</b></div><div class="allocation-row"><span>EPS</span><div class="bar blue"><span style="width:92%"></span></div><b>+51%</b></div><div class="allocation-row"><span>FCF</span><div class="bar gold"><span style="width:79%"></span></div><b>+36%</b></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Valuation</h2><p>Forward multiples versus history</p></div></div><div class="panel-body"><div class="list"><div class="list-row"><div><b>Forward P/E</b><small>5-year range 24×–72×</small></div><b>36.4×</b></div><div class="list-row"><div><b>EV / Sales</b><small>Peer median 12.8×</small></div><b>18.2×</b></div><div class="list-row"><div><b>FCF yield</b><small>5-year median 2.4%</small></div><b>2.1%</b></div></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Latest evidence</h2><p>News, analysts, and filings</p></div></div><div class="panel-body list"><div class="list-row"><span class="list-icon">${icon("newspaper")}</span><div><b>Major cloud buyer expands accelerator order</b><small>Positive · 3 hours ago</small></div></div><div class="list-row"><span class="list-icon">${icon("trending-up")}</span><div><b>Consensus EPS estimate rises 2.3%</b><small>Positive · Yesterday</small></div></div><div class="list-row"><span class="list-icon">${icon("file-check-2")}</span><div><b>10-Q evidence incorporated</b><small>Verified · Aug 26</small></div></div></div></article></section>`;
  initializePage();
  drawPerformanceChart("security-chart", true);
}

function renderPortfolio() {
  const holdings = securities.filter(item => item.owned);
  pageContent.innerHTML = pageHeading("Paper account", "Portfolio", "Performance, positions, allocation, and risk for the simulated Atlas portfolio.", `<select class="button"><option>Atlas Paper Portfolio</option></select><button class="button">${icon("download")} Export</button><button class="button primary">${icon("wand-sparkles")} Review rebalance</button>`)
    + `<section class="grid cols-4"><article class="panel metric"><small>Total value</small><strong>$104,820</strong><span class="positive">+$4,820 all time</span></article><article class="panel metric"><small>Invested</small><strong>$73,360</strong><span>70.0% exposure</span></article><article class="panel metric"><small>Unrealized gain</small><strong>$3,940</strong><span class="positive">+5.68%</span></article><article class="panel metric"><small>Risk level</small><strong>Moderate</strong><span class="warning">2 concentration flags</span></article></section><div class="spacer"></div>
    <section class="grid two-one"><article class="panel"><div class="panel-heading"><div><h2>Performance</h2><p>Portfolio growth after simulated costs</p></div><div class="segment-control"><button>1M</button><button class="active">3M</button><button>1Y</button><button>All</button></div></div><div class="chart-wrap"><canvas id="portfolio-chart"></canvas><div class="chart-legend"><span><i class="legend-dot"></i>Atlas +4.82%</span><span><i class="legend-dot spy"></i>SPY +6.08%</span><span><i class="legend-dot qqq"></i>QQQ +5.44%</span></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Allocation</h2><p>Current weight by sector</p></div></div><div class="panel-body"><div class="allocation-row"><span>Cash</span><div class="bar gold"><span style="width:30%"></span></div><b>30%</b></div><div class="allocation-row"><span>Software</span><div class="bar"><span style="width:26%"></span></div><b>26%</b></div><div class="allocation-row"><span>Semiconductors</span><div class="bar blue"><span style="width:18%"></span></div><b>18%</b></div><div class="allocation-row"><span>Consumer</span><div class="bar red"><span style="width:14%"></span></div><b>14%</b></div><div class="allocation-row"><span>Defense</span><div class="bar"><span style="width:12%"></span></div><b>12%</b></div><div class="callout risk"><strong>Concentration review</strong>Software exposure is 6 points above the target range.</div></div></article></section><div class="spacer"></div>
    <section class="panel table-panel"><div class="panel-heading"><div><h2>Current holdings</h2><p>${holdings.length} simulated positions · sorted by market value</p></div><div class="segment-control"><button class="active">Positions</button><button>Lots</button><button>Closed</button></div></div><table class="data-table"><thead><tr><th>Holding</th><th>Atlas view</th><th>Shares</th><th>Price</th><th>Market value</th><th>Weight</th><th>Total return</th><th>Day</th><th>Next action</th></tr></thead><tbody>${holdings.map((item,index) => `<tr><td>${tickerCell(item)}</td><td><span class="tag ${actionClass(item.action)}">${item.action}</span></td><td>${[18,24,42,16,29,12][index] || 10}</td><td>$${item.price.toFixed(2)}</td><td>$${[9650,7604,6392,7971,6653,8176][index].toLocaleString()}</td><td>${[9.2,7.3,6.1,7.6,6.3,7.8][index]}%</td><td class="${index===4?"negative":"positive"}">${index===4?"-2.11%":`+${(2.4+index*1.13).toFixed(2)}%`}</td><td class="${item.move>=0?"positive":"negative"}">${signed(item.move)}</td><td>${item.action === "Trim" ? "Reduce to 6%" : item.action === "Exit" ? "Review exit" : "Monitor"}</td></tr>`).join("")}</tbody></table></section><div class="spacer"></div>
    <section class="grid cols-3"><article class="panel"><div class="panel-heading"><div><h2>Risk summary</h2><p>Portfolio-level exposure checks</p></div></div><div class="panel-body list"><div class="list-row"><span class="list-icon warning">${icon("layers-3")}</span><div><b>Sector concentration</b><small>Software is above its target range.</small></div><span class="tag risk">Review</span></div><div class="list-row"><span class="list-icon positive">${icon("shield-check")}</span><div><b>Cash reserve</b><small>30% is above the 20% minimum.</small></div><span class="tag buy">Clear</span></div><div class="list-row"><span class="list-icon positive">${icon("waves")}</span><div><b>Drawdown</b><small>-3.8% versus -10% limit.</small></div><span class="tag buy">Clear</span></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Return attribution</h2><p>Largest contributors and detractors</p></div></div><div class="panel-body"><div class="allocation-row"><span>MSFT</span><div class="bar"><span style="width:82%"></span></div><b>+1.42%</b></div><div class="allocation-row"><span>PLTR</span><div class="bar"><span style="width:56%"></span></div><b>+0.88%</b></div><div class="allocation-row"><span>AMZN</span><div class="bar red"><span style="width:28%"></span></div><b>-0.31%</b></div></div></article><article class="panel"><div class="panel-heading"><div><h2>Scenario check</h2><p>Estimated portfolio sensitivity</p></div></div><div class="panel-body"><div class="list"><div class="list-row"><div><b>Nasdaq -10%</b><small>Growth shock estimate</small></div><b class="negative">-7.4%</b></div><div class="list-row"><div><b>Rates +1%</b><small>Duration sensitivity</small></div><b class="negative">-3.1%</b></div><div class="list-row"><div><b>Defense +10%</b><small>Sector upside estimate</small></div><b class="positive">+1.2%</b></div></div></div></article></section>`;
  initializePage();
  drawPerformanceChart("portfolio-chart");
}

function renderActivity() {
  pageContent.innerHTML = pageHeading("Decision history", "Activity", "A complete record of Atlas recommendations, owner decisions, and simulated transactions.", `<button class="button">${icon("sliders-horizontal")} Filter</button><button class="button">${icon("download")} Export audit log</button>`)
    + `<section class="grid cols-4"><article class="panel metric"><small>Recommendations</small><strong>67</strong><span>Current policy period</span></article><article class="panel metric"><small>Simulated buys</small><strong>21</strong><span class="positive">57% judged working</span></article><article class="panel metric"><small>Simulated sells</small><strong>14</strong><span class="positive">+0.8% avg decision edge</span></article><article class="panel metric"><small>Open decisions</small><strong>2</strong><span class="warning">Owner review requested</span></article></section><div class="spacer"></div>
    <section class="panel"><div class="tabs"><button class="active">All activity</button><button>Recommendations</button><button>Transactions</button><button>Owner decisions</button><button>Policy changes</button></div><div class="filter-bar"><select><option>Last 30 days</option><option>Last 90 days</option><option>All history</option></select><input type="search" placeholder="Filter by ticker"><span class="filter-count">12 recent events</span></div><div class="panel-body timeline">
      <div class="timeline-item"><b>Atlas recommended a simulated NVDA purchase</b><small>Today, 7:05 AM · 5.0% target weight · Score 94 · Awaiting entry condition</small></div>
      <div class="timeline-item"><b>AMZN trim review opened</b><small>Today, 7:05 AM · Position exceeded its target and relative strength weakened</small></div>
      <div class="timeline-item"><b>Simulated AVGO purchase recorded</b><small>Aug 28, 7:06 AM · 24 shares at $314.82 · Automatic paper mode</small></div>
      <div class="timeline-item"><b>META exit recommendation created</b><small>Aug 28, 7:05 AM · Trend and estimate confirmation deteriorated</small></div>
      <div class="timeline-item"><b>Weekly strategy review completed</b><small>Aug 23, 8:04 AM · No policy settings changed</small></div>
      <div class="timeline-item"><b>Entry experiment result retained by owner</b><small>Aug 14, 3:18 PM · Typed owner confirmation · Paper policy only</small></div>
    </div></section>`;
  initializePage();
}

function renderReports() {
  pageContent.innerHTML = pageHeading("Research library", "Reports", "Read, search, download, and share Atlas research products.", `<button class="button">${icon("search")} Search reports</button><button class="button primary">${icon("mail")} Email latest brief</button>`)
    + `<section class="panel report-layout"><aside class="report-list">${reports.map((report,index) => `<button class="report-item ${index===0?"active":""}" data-report="${index}"><span class="tag ${report.type.includes("Risk")?"risk":""}">${report.type}</span><b>${report.title}</b><small>${report.date} · ${report.read}</small></button>`).join("")}</aside><article class="report-reader"><p class="eyebrow">Morning Executive Brief · August 29, 2026</p><h2>AI leadership broadens as market breadth improves</h2><div class="callout"><strong>Executive view</strong>The market remains constructive but selective. Atlas favors high-quality AI infrastructure while preserving cash for volatility around next week's earnings and employment data.</div><h3>What changed</h3><p>Market breadth improved to 61% across the Atlas universe, with semiconductors, software, and cybersecurity outperforming. Consumer growth weakened, and two current holdings moved into active review.</p><h3>Recommended actions</h3><ul><li><strong>Buy candidate:</strong> NVIDIA entered the preferred range with a 94 Atlas Score and strong confirmation.</li><li><strong>Trim review:</strong> Amazon is above its target weight while relative momentum softens.</li><li><strong>Exit review:</strong> Meta breached the current paper risk threshold after a third weak observation.</li></ul><h3>Portfolio context</h3><p>The paper portfolio gained 0.59% today but remains 1.26 percentage points behind SPY since inception. Cash is 30%, giving Atlas room to add one high-conviction position without breaching the minimum reserve.</p><h3>Risks to watch</h3><p>NVIDIA earnings and the US employment report could increase volatility. Atlas will not change policy or expand position limits based on a single event.</p><p><small>Prototype content for product-design review. Not investment advice and not a live order.</small></p></article></section>`;
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
  pageContent.querySelectorAll("[data-security]").forEach(button => button.addEventListener("click", () => { sessionStorage.setItem("atlasTicker", button.dataset.security); location.hash = "research"; }));
  pageContent.querySelectorAll("[data-watch]").forEach(button => button.addEventListener("click", () => showToast(`${button.dataset.watch} added to your prototype watchlist.`)));
  pageContent.querySelectorAll(".segment-control button:not([disabled])").forEach(button => button.addEventListener("click", () => { button.parentElement.querySelectorAll("button").forEach(item => item.classList.remove("active")); button.classList.add("active"); showToast(`View changed to ${button.textContent.trim()}.`); }));
  pageContent.querySelectorAll(".tabs button").forEach(button => button.addEventListener("click", () => { button.parentElement.querySelectorAll("button").forEach(item => item.classList.remove("active")); button.classList.add("active"); }));
  pageContent.querySelectorAll(".switch").forEach(button => button.addEventListener("click", () => button.classList.toggle("on")));
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
  const name = location.hash.replace("#", "") || "today";
  document.querySelectorAll(".nav-link").forEach(link => link.classList.toggle("active", link.dataset.route === name));
  document.querySelector(".sidebar").classList.remove("open");
  const routes = {
    today: renderToday,
    discover: renderDiscover,
    research: () => renderResearch(sessionStorage.getItem("atlasTicker") || "NVDA"),
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
  searchResults.querySelectorAll("[data-search-ticker]").forEach(button => button.addEventListener("click", () => { sessionStorage.setItem("atlasTicker",button.dataset.searchTicker); searchResults.hidden = true; searchInput.value = ""; location.hash = "research"; route(); }));
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
