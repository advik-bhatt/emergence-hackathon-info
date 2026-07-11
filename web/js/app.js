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
  rules: null, // decide()'s thresholds, served by /runtime
};

// Mirrors analysis/verdict.py::decide() — thresholds come from the backend.
function decideVerdict(promised, median, p95, rules) {
  const gap = p95 - promised;
  if (gap <= rules.ok_tolerance_days) return "OK";
  const tail = p95 - median;
  if (tail / p95 >= rules.variance_dominant_share && tail >= rules.min_tail_days_for_fix) return "FIX";
  return "PAD";
}

// Mirrors analysis/verdict.py::flip_distance_days() (60d search horizon is plenty here).
function flipDistanceDays(promised, median, p95, rules) {
  const current = decideVerdict(promised, median, p95, rules);
  for (let d = 0.1; d <= 60; d = Math.round((d + 0.1) * 10) / 10) {
    for (const dir of [1, -1]) {
      const candidate = p95 + dir * d;
      if (candidate < 0) continue;
      if (decideVerdict(promised, median, candidate, rules) !== current) return d;
    }
  }
  return 60;
}

let race;
let lastRatioText; // previous "1 in N" so we can pop it when it changes

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
  // the duel: false number vs the truth
  countUp($("chip-days-n"), quote.current_promise, { duration: 700 });
  countUp($("pd-engine-n"), quote.days, { duration: 900 });
  const duel = $("promise-duel");
  duel.classList.remove("struck");
  if (quote.verdict !== "OK") {
    void duel.offsetWidth; // restart the strike transition
    duel.classList.add("struck");
  }
  const pill = $("pd-delta");
  const delta = Math.round(quote.days - quote.current_promise);
  const label =
    quote.verdict === "FIX" ? `${delta >= 0 ? "+" : ""}${delta}d short — fix the tail` :
    quote.verdict === "PAD" ? `+${delta}d short — honestly far` :
    "calibrated — keep it";
  const pillChanged = pill.dataset.prev !== undefined && pill.dataset.prev !== label;
  pill.className = `pd-delta ${quote.verdict.toLowerCase()}`;
  pill.textContent = label;
  if (pillChanged) {
    void pill.offsetWidth;
    pill.classList.add("changed");
  }
  pill.dataset.prev = label;

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
  const ratioText = n <= 12 ? `1 in ${n}` : `${fmt(rate, 1)}%`;
  caption.textContent = "…breaks its word to ";
  const ratio = document.createElement("b");
  ratio.textContent = ratioText;
  caption.appendChild(ratio);
  caption.append(n <= 12 ? " of these customers" : " of customers");
  if (lastRatioText !== undefined && lastRatioText !== ratioText) {
    ratio.classList.add("changed"); // fresh node → the pop plays immediately
  }
  lastRatioText = ratioText;
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
    { label: "Your handling — sale → carrier handoff", tag: "your handling",
      value: quote.handling_days, varName: "--seg-handling", yours: true },
    { label: "Distance — median carrier transit", tag: "distance",
      value: quote.transit_median_days, varName: "--seg-median" },
    { label: "The tail — variance allowance (p95 − median)", tag: "the tail",
      value: quote.transit_tail_days, varName: "--seg-tail" },
  ];
  if (Math.abs(quote.season_days) > 0.01) {
    segments.push({ label: "Season load — this month's history", tag: "season",
      value: quote.season_days, varName: "--seg-season" });
  }
  const total = segments.reduce((s, seg) => s + Math.max(seg.value, 0), 0) || 1;
  segments.forEach((seg, i) => {
    const pct = Math.max(seg.value, 0) / total;
    const el = document.createElement("div");
    el.className = "bar-segment";
    el.style.width = `${pct * 100}%`;
    el.style.background = `var(${seg.varName})`;
    el.style.transitionDelay = `${i * 130}ms`;
    if (pct > 0.13) {
      // wide segment: number + its role, stacked
      const n = document.createElement("b");
      n.textContent = `${fmt(seg.value, 0)}d`;
      const t = document.createElement("i");
      t.textContent = seg.tag;
      el.append(n, t);
    } else if (pct > 0.055) {
      const n = document.createElement("b");
      n.textContent = `${fmt(seg.value, 0)}d`;
      el.appendChild(n);
    }
    el.title = `${seg.label}: ${fmt(seg.value, 1)}d`;
    bar.appendChild(el);

    const item = document.createElement("div");
    item.className = "legend-item" + (seg.yours ? " yours" : "");
    const sw = document.createElement("span");
    sw.className = "legend-swatch";
    sw.style.background = `var(${seg.varName})`;
    item.append(sw, `${seg.label} — ${fmt(seg.value, 1)}d`);
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

  // robustness dial + live stress-test: drag the tail, the same rule re-decides
  const dial = $("flip-dial");
  const setDial = (flip, borderline, stroke) => {
    const conf = Math.min(Math.abs(flip) / 8, 1); // 8+ days to flip = fully robust
    $("dial-fill").style.strokeDashoffset = 252 - conf * 252;
    $("dial-fill").style.stroke = stroke;
    $("dial-needle").style.transform = `rotate(${-90 + conf * 180}deg)`;
    dial.classList.toggle("trembling", borderline);
  };

  const stress = $("stress-slider");
  const baseP95 = quote.lane_p95_days;
  const med = quote.lane_median_days;
  const prom = quote.current_promise;
  stress.value = 0;

  const applyStress = () => {
    const shift = stress.value / 10;
    const p95 = Math.max(baseP95 + shift, 0);
    $("stress-val").textContent =
      `p95 = ${fmt(p95, 1)}d (${shift >= 0 ? "+" : ""}${fmt(shift, 1)})`;
    $("stress-reset").hidden = shift === 0;
    const sv = $("stress-verdict");

    if (shift === 0 || !state.rules) {
      // at rest: show exactly what the server said
      setDial(quote.flip_distance ?? 0, !!quote.is_borderline,
        quote.is_borderline ? "var(--amber)" : "var(--phosphor)");
      $("flip-label").textContent = quote.is_borderline
        ? `trembling — the verdict flips if p95 moves ±${fmt(quote.flip_distance, 1)} days`
        : `robust — p95 would have to move ${fmt(quote.flip_distance, 1)} days to flip this verdict`;
      sv.className = `stress-verdict ${quote.verdict.toLowerCase()}`;
      sv.textContent = `${quote.verdict} — holds`;
      return;
    }

    const v = decideVerdict(prom, med, p95, state.rules);
    const fd = flipDistanceDays(prom, med, p95, state.rules);
    const flipped = v !== quote.verdict;
    setDial(fd, fd < 1,
      flipped ? "var(--signal)" : fd < 1 ? "var(--amber)" : "var(--phosphor)");
    $("flip-label").textContent = flipped
      ? `FLIPPED — at a ${fmt(p95, 1)}-day tail this lane becomes ${v}`
      : fd < 1
        ? `still ${v} — but now ±${fmt(fd, 1)} days from flipping`
        : `still ${v} — ${fmt(fd, 1)} more days to flip`;
    const svClassNow = `stress-verdict ${v.toLowerCase()}${flipped ? " flipped" : ""}`;
    if (sv.className !== svClassNow) {
      sv.className = svClassNow; // fresh class set restarts the pop animation
    }
    sv.textContent = flipped ? `${v} — flipped` : `${v} — holds`;
  };
  stress.oninput = applyStress;
  $("stress-reset").onclick = () => { stress.value = 0; applyStress(); };
  applyStress();

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
  state.rules = runtime.verdict_rules || null;

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

  initTrail(investigation, runtime, lanes);
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
