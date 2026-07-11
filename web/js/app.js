// app.js — boot + checkout sim + wiring. Every figure traces to a fixture.
import { $, fmt, getJSON, countUp, onInView, initTilt, initGlassGlow, initReceipts, sleep } from "./fx.js";
import { initMap } from "./map3d.js";
import { initSeason, initRace, initStars, initQueue } from "./sections.js";
import { initTrail, initTrap } from "./trail.js";

const STATE_NAMES = {
  AC: "Acre", AL: "Alagoas", AP: "Amapá", AM: "Amazonas", BA: "Bahia", CE: "Ceará",
  DF: "Distrito Federal", ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão",
  MT: "Mato Grosso", MS: "Mato Grosso do Sul", MG: "Minas Gerais", PA: "Pará",
  PB: "Paraíba", PR: "Paraná", PE: "Pernambuco", PI: "Piauí", RJ: "Rio de Janeiro",
  RN: "Rio Grande do Norte", RS: "Rio Grande do Sul", RO: "Rondônia", RR: "Roraima",
  SC: "Santa Catarina", SP: "São Paulo", SE: "Sergipe", TO: "Tocantins",
};

const state = {
  seller: null,
  dest: "RJ",
  month: null,
  monthLabel: null,
  quote: null,
  lanesByState: {},
};

let race;

/* ── seller aliases: a persona can't care about a hex id ───────── */
function sellerAlias(s, idx) {
  const p95 = s.handling_p95_days;
  const tier = p95 <= 4 ? "Fast-handoff" : p95 <= 9 ? "Steady" : p95 <= 18 ? "Slow-handoff" : "Backlog-prone";
  return `${tier} seller · ${fmt(p95, 1)}d handling p95`;
}

/* ── checkout quote ─────────────────────────────────────────────── */
async function refreshQuote() {
  if (!state.seller || !state.dest) return;
  const body = { seller_id: state.seller, state: state.dest };
  if (state.month) { body.month = state.month; body.seasonal = true; }

  let quote;
  try {
    quote = await getJSON("/promise", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return;
  }
  state.quote = quote;
  renderCheckout(quote);
  renderBreakdown(quote);
  const lane = state.lanesByState[state.dest];
  if (lane && race) race.setLane(lane);
}

function renderCheckout(quote) {
  countUp($("chip-days-n"), quote.current_promise, { duration: 700 });

  // "breaks its word to 1 in N" avatars
  const row = $("avatar-row");
  row.innerHTML = "";
  const rate = quote.late_rate;
  const n = Math.round(100 / Math.max(rate, 0.1));
  const shown = Math.min(Math.max(n, 2), 12);
  for (let i = 0; i < shown; i++) {
    const a = document.createElement("span");
    a.className = "avatar";
    row.appendChild(a);
  }
  const caption = $("avatar-caption");
  if (n <= 12) {
    caption.textContent = `…breaks its word to 1 in ${n} of these customers`;
  } else {
    caption.textContent = `…breaks its word to ${fmt(rate, 1)}% of customers`;
  }
  // snap one avatar red after a beat
  setTimeout(() => {
    const victims = row.querySelectorAll(".avatar");
    victims[Math.min(2, victims.length - 1)]?.classList.add("broken");
  }, 700);
}

function renderBreakdown(quote) {
  countUp($("current-days"), quote.current_promise, { duration: 900 });
  countUp($("engine-days"), quote.days, { duration: 1200 });
  $("current-consequence").textContent =
    `breaks its word to ${fmt(quote.late_rate, 1)}% of customers`;

  // decomposition
  const bar = $("decomp-bar");
  const legend = $("decomp-legend");
  bar.classList.remove("built");
  bar.innerHTML = "";
  legend.innerHTML = "";
  const segments = [
    { label: "Seller handling", value: quote.handling_days, varName: "--seg-handling", yours: true },
    { label: "Lane transit (median)", value: quote.transit_median_days, varName: "--seg-median" },
    { label: "Lane transit (tail)", value: quote.transit_tail_days, varName: "--seg-tail" },
  ];
  if (Math.abs(quote.season_days) > 0.01) {
    segments.push({ label: "Seasonal load", value: quote.season_days, varName: "--seg-season" });
  }
  const total = segments.reduce((s, seg) => s + Math.max(seg.value, 0), 0) || 1;
  segments.forEach((seg, i) => {
    const el = document.createElement("div");
    el.className = "bar-segment";
    el.style.width = `${(Math.max(seg.value, 0) / total) * 100}%`;
    el.style.background = `var(${seg.varName})`;
    el.style.transitionDelay = `${i * 130}ms`;
    if ((Math.max(seg.value, 0) / total) > 0.1) el.textContent = `${fmt(seg.value, 0)}d`;
    el.title = `${seg.label}: ${fmt(seg.value, 1)}d`;
    bar.appendChild(el);

    const item = document.createElement("div");
    item.className = "legend-item" + (seg.yours ? " yours" : "");
    const sw = document.createElement("span");
    sw.className = "legend-swatch";
    sw.style.background = `var(${seg.varName})`;
    item.append(sw, `${seg.label}${seg.yours ? " (yours)" : ""} — ${fmt(seg.value, 1)}d`);
    legend.appendChild(item);
  });
  requestAnimationFrame(() => requestAnimationFrame(() => bar.classList.add("built")));

  // verdict stamp
  const stamp = $("verdict-stamp");
  stamp.classList.remove("stamped", "fix", "pad", "keep");
  $("verdict-tag").textContent = quote.verdict;
  stamp.classList.add(quote.verdict.toLowerCase());
  requestAnimationFrame(() => requestAnimationFrame(() => stamp.classList.add("stamped")));
  $("verdict-text").textContent = verdictCopy(quote);
  $("fallback-note").hidden = !quote.handling_is_fallback;

  const chipRow = $("chip-row");
  chipRow.innerHTML = "";
  if (quote.is_borderline) {
    const chip = document.createElement("span");
    chip.className = "chip borderline";
    chip.textContent = `borderline — verdict flips on ±${fmt(quote.flip_distance, 1)} days`;
    chipRow.appendChild(chip);
  }

  // robustness dial: more flip-distance = more buried needle
  const flip = Math.abs(quote.flip_distance ?? 0);
  const conf = Math.min(flip / 8, 1); // 8+ days to flip = fully robust
  const dial = $("flip-dial");
  $("dial-fill").style.strokeDashoffset = 252 - conf * 252;
  $("dial-fill").style.stroke = quote.is_borderline ? "var(--amber)" : "var(--phosphor)";
  $("dial-needle").style.transform = `rotate(${-90 + conf * 180}deg)`;
  dial.classList.toggle("trembling", !!quote.is_borderline);
  $("flip-label").textContent = quote.is_borderline
    ? `trembling — the verdict flips if p95 moves ±${fmt(flip, 1)} days`
    : `robust — p95 would have to move ${fmt(flip, 1)} days to flip this verdict`;

  // what-if handling slider
  const slider = $("whatif-slider");
  const maxCut = Math.max(quote.handling_days - 0.5, 0);
  slider.max = Math.round(maxCut * 10);
  slider.value = 0;
  $("whatif-value").textContent = "−0.0 days handling";
  $("whatif-days").textContent = fmt(quote.days, 0);
  slider.oninput = () => {
    const cut = slider.value / 10;
    $("whatif-value").textContent = `−${fmt(cut, 1)} days handling`;
    $("whatif-days").textContent = fmt(Math.max(quote.days - cut, 1), 0);
  };
}

function verdictCopy(quote) {
  if (quote.verdict === "FIX") {
    if (quote.state === "RJ") {
      return `Don't pad it — fix it. Rio's median is ${fmt(quote.lane_median_days, 0)} days. ` +
        `Padding to ${fmt(quote.lane_p95_days, 0)} would make your #2 market look worse than Pará.`;
    }
    return `Don't pad it — fix it. ${quote.state}'s median is ${fmt(quote.lane_median_days, 0)} days ` +
      `— padding the promise out to its ${fmt(quote.lane_p95_days, 0)}-day p95 would make an ` +
      `already-fine typical delivery look absurd. Attack the tail instead.`;
  }
  if (quote.verdict === "PAD") return "Padding is honest — this lane really is far away.";
  return "Already calibrated. No action — and we're not crying wolf.";
}

/* ── destination selection (map → checkout) ─────────────────────── */
function setDestination(lane) {
  state.dest = lane.state;
  $("dest-state").textContent = lane.state;
  $("dest-name").textContent = STATE_NAMES[lane.state] || lane.state;
  refreshQuote();
}

/* ── boot ───────────────────────────────────────────────────────── */
(async () => {
  // loading line theater — the replay architecture is the feature
  const loadingLine = $("map-loading-line");
  const slugs = ["lanes … 17 rows", "state_transit … 17 rows", "seasonality … 20 rows",
    "seller_handling … 461 rows", "review_damage … 6 rows", "churn … 6 rows"];
  let li = 0;
  const loadTicker = setInterval(() => {
    loadingLine.textContent = `replaying CRAFT fixture: ${slugs[li++ % slugs.length]}`;
  }, 420);

  const [runtime, lanesData, sellersData, seasonData, receiptsData, investigation] =
    await Promise.all([
      getJSON("/runtime").catch(() => ({})),
      getJSON("/lanes"),
      getJSON("/sellers"),
      getJSON("/seasonality").catch(() => ({ months: [] })),
      getJSON("/receipts").catch(() => ({ receipts: {} })),
      getJSON("/investigation"),
    ]);

  const lanes = lanesData.lanes;
  lanes.forEach((l) => { state.lanesByState[l.state] = l; });

  // HUD truth badges — rendered verbatim from /runtime
  if (runtime.model) {
    $("badge-model-text").textContent =
      `${runtime.model.split("/").pop()} · ${runtime.inference || "Nebius Token Factory"}`;
  }
  $("badge-mode").textContent =
    (runtime.mode || "replay").toUpperCase() + (runtime.llm_configured ? " · LIVE LLM" : "");
  $("engine-chip-model").lastChild.textContent =
    ` reasoning: ${(runtime.model || "scripted").split("/").pop()} · Nebius`;

  // sellers (aliased, real id on hover)
  const sellerSelect = $("seller-select");
  sellerSelect.innerHTML = "";
  sellersData.sellers.forEach((s, i) => {
    const opt = document.createElement("option");
    opt.value = s.seller_id;
    opt.textContent = sellerAlias(s, i);
    opt.title = s.seller_id;
    sellerSelect.appendChild(opt);
  });
  state.seller = sellersData.sellers[0]?.seller_id;
  sellerSelect.addEventListener("change", () => {
    state.seller = sellerSelect.value;
    refreshQuote();
  });

  // KPI odometers
  const totalOrders = lanes.reduce((s, l) => s + l.orders, 0);
  const totalRisk = lanes.reduce((s, l) => s + l.orders_at_risk, 0);
  countUp($("kpi-orders"), totalOrders, { duration: 2200 });
  countUp($("kpi-lanes"), lanes.length, { duration: 1400 });
  countUp($("kpi-risk"), totalRisk, { duration: 2600 });

  // sections
  race = initRace();
  const season = initSeason(seasonData.months, {
    onPickMonth(month, label) {
      state.month = month;
      state.monthLabel = label;
      $("month-chip").hidden = false;
      $("month-chip-text").textContent = `${label} load applied`;
      refreshQuote();
    },
  });
  $("month-chip-clear").addEventListener("click", () => {
    state.month = null;
    $("month-chip").hidden = true;
    season.clearSelection();
    refreshQuote();
  });

  initTrail(investigation, runtime);
  if (investigation.trap) initTrap(investigation.trap);
  if (receiptsData.receipts.review_damage) {
    initStars(receiptsData.receipts.review_damage.rows);
  }
  initQueue(lanes);
  initReceipts(receiptsData.receipts);
  initTilt();
  initGlassGlow();

  $("cta-breakdown").addEventListener("click", () => {
    $("stage-breakdown").scrollIntoView({ behavior: "smooth" });
  });

  // the map (heaviest — last; loading veil holds until it's up)
  try {
    const map = await initMap({
      container: $("map-wrap"),
      lanes,
      onSelect: setDestination,
    });
    map.selectState("RJ");
  } catch (err) {
    console.error("map failed, continuing without it:", err);
  }
  clearInterval(loadTicker);
  $("map-loading").classList.add("done");

  // first quote + arm the race for its first scroll-in
  await refreshQuote();
  const firstLane = state.lanesByState[state.dest];
  if (firstLane) race.arm(firstLane);
})().catch((err) => {
  console.error("boot failed:", err);
  $("map-loading-line").textContent = "boot failed — is the API running? uvicorn promise_engine.api.app:app";
});
