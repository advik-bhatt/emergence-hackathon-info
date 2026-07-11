// The Promise Engine — no build step, no framework, no CDN.
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  // ---------------- tabs ----------------

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => {
        b.classList.remove("is-active");
        b.setAttribute("aria-selected", "false");
      });
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("is-active"));
      btn.classList.add("is-active");
      btn.setAttribute("aria-selected", "true");
      $(`tab-${btn.dataset.tab}`).classList.add("is-active");
    });
  });

  // ---------------- helpers ----------------

  const fmt = (n, digits = 0) =>
    Number(n).toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });

  const shortId = (id) => id.slice(0, 8) + "…";

  async function getJSON(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`${url} -> ${res.status}`);
    return res.json();
  }

  // ---------------- checkout tab ----------------

  const sellerSelect = $("seller-select");
  const stateSelect = $("state-select");
  const bfToggle = $("black-friday-toggle");

  async function loadCheckoutInputs() {
    const [sellersData, statesData] = await Promise.all([
      getJSON("/sellers"),
      getJSON("/states"),
    ]);

    sellerSelect.innerHTML = "";
    sellersData.sellers.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.seller_id;
      opt.textContent = `${shortId(s.seller_id)} — ${fmt(s.handling_p95_days, 1)}d handling`;
      sellerSelect.appendChild(opt);
    });

    stateSelect.innerHTML = "";
    statesData.states.forEach((state) => {
      const opt = document.createElement("option");
      opt.value = state;
      opt.textContent = state;
      stateSelect.appendChild(opt);
    });
    if (statesData.states.includes("RJ")) stateSelect.value = "RJ";
  }

  function verdictCopy(verdict, quote) {
    if (verdict === "FIX") {
      if (quote.state === "RJ") {
        return (
          `Don't pad it — fix it. Rio's median is ${fmt(quote.lane_median_days, 0)} days. ` +
          `Padding to ${fmt(quote.lane_p95_days, 0)} would make your #2 market look worse than Pará.`
        );
      }
      return (
        `Don't pad it — fix it. ${quote.state}'s median is ${fmt(quote.lane_median_days, 0)} days ` +
        `— padding the promise out to its ${fmt(quote.lane_p95_days, 0)}-day p95 would make an ` +
        `already-fine typical delivery look absurd. Attack the tail instead.`
      );
    }
    if (verdict === "PAD") {
      return "Padding is honest — this lane really is far away.";
    }
    return "Already calibrated. No action.";
  }

  function renderDecomposition(quote) {
    const bar = $("stacked-bar");
    const legend = $("bar-legend");
    bar.innerHTML = "";
    legend.innerHTML = "";

    const segments = [
      { label: "Seller handling", value: quote.handling_days, color: "var(--seg-handling)" },
      { label: "Lane transit (median)", value: quote.transit_median_days, color: "var(--seg-median)" },
      { label: "Lane transit (tail)", value: quote.transit_tail_days, color: "var(--seg-tail)" },
    ];
    if (Math.abs(quote.season_days) > 0.01) {
      segments.push({ label: "Seasonal adjustment", value: quote.season_days, color: "var(--seg-season)" });
    }

    const total = segments.reduce((sum, seg) => sum + Math.max(seg.value, 0), 0) || 1;

    segments.forEach((seg) => {
      const pct = (Math.max(seg.value, 0) / total) * 100;
      const el = document.createElement("div");
      el.className = "bar-segment";
      el.style.width = pct + "%";
      el.style.background = seg.color;
      el.title = `${seg.label}: ${fmt(seg.value, 1)}d`;
      if (pct > 10) el.textContent = `${fmt(seg.value, 0)}d`;
      bar.appendChild(el);

      const item = document.createElement("div");
      item.className = "legend-item";
      const swatch = document.createElement("span");
      swatch.className = "legend-swatch";
      swatch.style.background = seg.color;
      item.appendChild(swatch);
      const text = document.createElement("span");
      text.textContent = `${seg.label} — ${fmt(seg.value, 1)}d`;
      item.appendChild(text);
      legend.appendChild(item);
    });
  }

  async function refreshQuote() {
    const sellerId = sellerSelect.value;
    const state = stateSelect.value;
    if (!sellerId || !state) return;

    $("result-loading").hidden = false;
    $("result-body").hidden = true;

    const body = { seller_id: sellerId, state };
    if (bfToggle.checked) {
      body.month = 11;
      body.seasonal = true;
    }

    let quote;
    try {
      quote = await getJSON("/promise", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch (err) {
      $("result-loading").textContent = "Could not compute a quote for this selection.";
      return;
    }

    $("current-days").textContent = fmt(quote.current_promise, 0);
    $("current-consequence").textContent =
      `breaks its word to ${fmt(quote.late_rate, 1)}% of customers`;
    $("engine-days").textContent = fmt(quote.days, 0);

    renderDecomposition(quote);

    const banner = $("verdict-banner");
    banner.className = "verdict-banner " + quote.verdict.toLowerCase();
    $("verdict-tag").textContent = quote.verdict;
    $("verdict-text").textContent = verdictCopy(quote.verdict, quote);

    const chipRow = $("chip-row");
    chipRow.innerHTML = "";
    if (quote.is_borderline) {
      const chip = document.createElement("span");
      chip.className = "chip borderline";
      chip.textContent = `borderline — verdict flips on ±${fmt(quote.flip_distance, 1)} days`;
      chipRow.appendChild(chip);
    }

    $("fallback-note").hidden = !quote.handling_is_fallback;

    $("result-loading").hidden = true;
    $("result-body").hidden = false;
  }

  sellerSelect.addEventListener("change", refreshQuote);
  stateSelect.addEventListener("change", refreshQuote);
  bfToggle.addEventListener("change", refreshQuote);

  // ---------------- ops tab ----------------

  const STEP_DELAY_MS = 600;

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function renderStepsSequentially(steps) {
    const list = $("trace-list");
    list.innerHTML = "";
    for (const step of steps) {
      const row = document.createElement("div");
      row.className = "trace-step trace-step-entering";
      row.innerHTML = `
        <span class="trace-kind trace-kind-${step.kind}">${step.kind}</span>
        <span class="trace-tool">${step.tool}</span>
        <p class="trace-finding">${step.finding}</p>
      `;
      list.appendChild(row);
      // Force a reflow so the entering class's transition actually plays, then settle it.
      void row.offsetWidth;
      row.classList.remove("trace-step-entering");
      await sleep(STEP_DELAY_MS);
    }
  }

  function renderTrapChart(curve) {
    const svg = $("trap-chart");
    const width = 480;
    const height = 220;
    const padding = { top: 16, right: 16, bottom: 28, left: 40 };
    const plotW = width - padding.left - padding.right;
    const plotH = height - padding.top - padding.bottom;

    const xs = curve.map((p) => p.extra_days);
    const ys = curve.map((p) => p.avg_review);
    const xMin = Math.min(...xs);
    const xMax = Math.max(...xs);
    const yMin = Math.min(...ys) - 0.03;
    const yMax = Math.max(...ys) + 0.03;

    const xScale = (x) => padding.left + ((x - xMin) / (xMax - xMin)) * plotW;
    const yScale = (y) => padding.top + (1 - (y - yMin) / (yMax - yMin)) * plotH;

    const linePath = curve
      .map((p, i) => `${i === 0 ? "M" : "L"}${xScale(p.extra_days).toFixed(1)},${yScale(p.avg_review).toFixed(1)}`)
      .join(" ");

    const areaPath =
      `${linePath} L${xScale(xMax).toFixed(1)},${(padding.top + plotH).toFixed(1)} ` +
      `L${xScale(xMin).toFixed(1)},${(padding.top + plotH).toFixed(1)} Z`;

    const gridLines = [0, 0.25, 0.5, 0.75, 1].map((t) => {
      const y = padding.top + t * plotH;
      return `<line x1="${padding.left}" y1="${y.toFixed(1)}" x2="${width - padding.right}" y2="${y.toFixed(1)}" class="trap-gridline" />`;
    }).join("");

    const xTickDays = [0, 5, 10, 15, 20, 25, 30].filter((d) => d <= xMax);
    const xTicks = xTickDays.map((d) => {
      const x = xScale(d);
      return `<text x="${x.toFixed(1)}" y="${height - 8}" class="trap-axis-label" text-anchor="middle">+${d}</text>`;
    }).join("");

    const yTicks = [yMin, (yMin + yMax) / 2, yMax].map((v) => {
      const y = yScale(v);
      return `<text x="${padding.left - 6}" y="${(y + 3).toFixed(1)}" class="trap-axis-label" text-anchor="end">${v.toFixed(2)}</text>`;
    }).join("");

    const last = curve[curve.length - 1];
    const dotX = xScale(last.extra_days);
    const dotY = yScale(last.avg_review);

    svg.innerHTML = `
      ${gridLines}
      <path d="${areaPath}" class="trap-area" />
      <path d="${linePath}" class="trap-line" />
      <circle cx="${dotX.toFixed(1)}" cy="${dotY.toFixed(1)}" r="4" class="trap-dot" />
      ${xTicks}
      ${yTicks}
      <text x="${width / 2}" y="${height - 8}" class="trap-axis-title" text-anchor="middle" dy="14">extra promise days (D)</text>
    `;
  }

  async function loadInvestigation() {
    const data = await getJSON("/investigation");
    const grid = $("hypothesis-grid");
    grid.innerHTML = "";
    data.hypotheses.forEach((h) => {
      const card = document.createElement("div");
      card.className = "hypothesis-card " + (h.status === "DEAD" ? "dead" : "survives");
      card.innerHTML = `
        <span class="hyp-status">${h.status}</span>
        <p class="hyp-claim">${h.claim}</p>
        <p class="hyp-evidence">${h.evidence}</p>
      `;
      grid.appendChild(card);
    });

    if (data.narrative) {
      $("narrative-card").hidden = false;
      $("narrative-text").textContent = data.narrative;
    }

    if (data.trap) {
      renderTrapChart(data.trap.curve);
      $("trap-caption").textContent =
        `Avg review climbs from ${fmt(data.trap.baseline_avg_review, 2)} to ` +
        `${fmt(data.trap.best_avg_review, 2)}/5 and flattens — the late rate falls to zero ` +
        `and nothing in the data ever says stop.`;
      $("trap-refusal-text").textContent = data.trap.why_we_refuse;
      $("trap-caveat-text").textContent = data.trap.caveat;
    }

    if (data.steps && data.steps.length) {
      renderStepsSequentially(data.steps);
    }
  }

  async function loadLanes() {
    const data = await getJSON("/lanes");
    const tbody = $("queue-tbody");
    tbody.innerHTML = "";
    data.lanes.forEach((lane, idx) => {
      const tr = document.createElement("tr");
      if (idx === 0) tr.className = "top-row";
      tr.innerHTML = `
        <td><span class="state-cell">${lane.state}</span></td>
        <td>${fmt(lane.orders, 0)}</td>
        <td>${fmt(lane.current_promise, 1)}</td>
        <td>${fmt(lane.median_days, 1)}</td>
        <td>${fmt(lane.p95_days, 1)}</td>
        <td>${lane.gap >= 0 ? "+" : ""}${fmt(lane.gap, 1)}</td>
        <td>${fmt(lane.late_rate, 1)}%</td>
        <td>${fmt(lane.orders_at_risk, 0)}</td>
        <td>
          <span class="verdict-chip ${lane.verdict.toLowerCase()}">${lane.verdict}</span>
          ${lane.is_borderline ? '<span class="borderline-mark">borderline</span>' : ""}
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // ---------------- boot ----------------

  (async () => {
    await loadCheckoutInputs();
    await refreshQuote();
    await Promise.all([loadInvestigation(), loadLanes()]);
  })().catch((err) => console.error("Failed to initialize:", err));
})();
