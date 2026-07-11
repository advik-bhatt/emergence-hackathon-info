// trail.js — the engine room (reasoning trail) and the trap cinematic.
import { $, fmt, sleep, typewriter, wordGenerate, onInView, shake, reducedMotion } from "./fx.js";

/* ═══════════ REASONING TRAIL ═══════════ */
export function initTrail(investigation, runtime, lanes = []) {
  const stepsEl = $("trail-steps");
  const beam = $("trail-beam");
  const modelVia = `${(runtime.model || "LLM").split("/").pop()} · Nebius`;
  let running = false;

  function beamTo(y) {
    if (reducedMotion) { beam.setAttribute("y2", y); return; }
    const from = Number(beam.getAttribute("y2")) || 0;
    const start = performance.now();
    const dur = 420;
    const tick = (now) => {
      const t = Math.min((now - start) / dur, 1);
      beam.setAttribute("y2", from + (y - from) * (1 - Math.pow(1 - t, 3)));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  async function play() {
    if (running) return;
    running = true;
    stepsEl.innerHTML = "";
    beam.setAttribute("y2", 0);
    $("hypothesis-grid").querySelectorAll(".hypothesis-card").forEach((c) => c.classList.remove("on"));
    $("narrative-card").hidden = true;

    for (const step of investigation.steps) {
      const row = document.createElement("div");
      row.className = `trace-step kind-${step.kind}`;

      const meta = document.createElement("div");
      meta.className = "trace-meta";
      const kind = document.createElement("span");
      kind.className = "trace-kind";
      kind.textContent = step.kind;
      const tool = document.createElement("span");
      tool.className = "trace-tool";
      tool.textContent = `${step.tool}()`;
      const via = document.createElement("span");
      via.className = "trace-via";
      via.textContent = step.kind === "refusal" || step.kind === "resolution"
        ? modelVia
        : "SQL · Emergence CRAFT";
      meta.append(kind, tool, via);
      row.appendChild(meta);

      const finding = document.createElement("p");
      finding.className = "trace-finding";
      row.appendChild(finding);
      stepsEl.appendChild(row);

      // reveal, grow beam to node, type the finding
      await sleep(60);
      row.classList.add("on");
      beamTo(row.offsetTop + 24);
      if (step.kind === "trap") shake();
      await typewriter(finding, step.finding, { cps: 90 });
      await sleep(reducedMotion ? 0 : 260);
    }

    // hypotheses cascade
    const cards = $("hypothesis-grid").querySelectorAll(".hypothesis-card");
    cards.forEach((c, i) => setTimeout(() => c.classList.add("on"), i * 140));

    // the conclusion: one line + verified stats, full text behind the fold
    if (investigation.narrative) {
      await sleep(cards.length * 140 + 250);
      $("narrative-card").hidden = false;
      $("verified-count").textContent = fmt(runtime.verified_numbers || 0);
      $("narrative-text").textContent = investigation.narrative;

      // the agent's own refusal line, verbatim if present
      const quote = investigation.narrative.match(/We will not optimize[^.]*\./)?.[0]
        || "We will not optimize a metric whose downside we cannot see.";
      wordGenerate($("concl-quote"), quote, { stagger: 60 });

      const dead = investigation.hypotheses.filter((h) => h.status === "DEAD").length;
      const survived = investigation.hypotheses.length - dead;
      const top = lanes[0];
      const grid = $("concl-grid");
      grid.innerHTML = "";
      const stats = [
        { n: `${dead} killed · ${survived} live`, l: "hypotheses, falsified first", alarm: false },
        { n: "+∞ REFUSED", l: "the review-max promise", alarm: true },
      ];
      if (top) {
        stats.push(
          { n: fmt(top.orders_at_risk), l: `order-days at risk — ${top.state} tops the queue`, alarm: true },
          { n: top.verdict, l: "fix the tail — don't pad the promise", alarm: false },
        );
      }
      stats.forEach((s, i) => {
        const el = document.createElement("div");
        el.className = "concl-stat" + (s.alarm ? " alarm" : "");
        const n = document.createElement("span");
        n.className = "cs-n";
        n.textContent = s.n;
        const l = document.createElement("span");
        l.className = "cs-l";
        l.textContent = s.l;
        el.append(n, l);
        grid.appendChild(el);
        setTimeout(() => el.classList.add("on"), 300 + i * 150);
      });
    }
    running = false;
  }

  // hypotheses DOM (content is static; reveal is animated per play())
  const grid = $("hypothesis-grid");
  grid.innerHTML = "";
  investigation.hypotheses.forEach((h) => {
    const card = document.createElement("div");
    card.className = "hypothesis-card " + (h.status === "DEAD" ? "dead" : "survives");
    const status = document.createElement("span");
    status.className = "hyp-status";
    status.textContent = h.status;
    const claim = document.createElement("p");
    claim.className = "hyp-claim";
    claim.textContent = h.claim;
    const evidence = document.createElement("p");
    evidence.className = "hyp-evidence";
    evidence.textContent = h.evidence;
    card.append(status, claim, evidence);
    grid.appendChild(card);
  });

  $("trail-replay").addEventListener("click", play);
  onInView($("stage-engine"), play, { threshold: 0.25 });
}

/* ═══════════ TRAP CINEMATIC ═══════════ */
export function initTrap(trap) {
  const stage = $("stage-trap");
  const slider = $("trap-slider");
  const status = $("tc-status");
  const curve = trap.curve;
  const maxDays = curve[curve.length - 1].extra_days;
  let playing = false;

  const at = (d) => {
    // nearest curve point at extra_days = d
    let best = curve[0];
    for (const p of curve) if (Math.abs(p.extra_days - d) < Math.abs(best.extra_days - d)) best = p;
    return best;
  };

  function drawChart(progress = 1) {
    const svg = $("trap-chart");
    const width = 480, height = 240;
    const pad = { top: 18, right: 18, bottom: 34, left: 44 };
    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;
    const xs = curve.map((p) => p.extra_days);
    const ys = curve.map((p) => p.avg_review);
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = Math.min(...ys) - 0.03, yMax = Math.max(...ys) + 0.03;
    const X = (x) => pad.left + ((x - xMin) / (xMax - xMin)) * plotW;
    const Y = (y) => pad.top + (1 - (y - yMin) / (yMax - yMin)) * plotH;

    const upto = curve.filter((p) => p.extra_days <= xMin + (xMax - xMin) * progress);
    const shown = upto.length >= 2 ? upto : curve.slice(0, 2);
    const line = shown.map((p, i) => `${i ? "L" : "M"}${X(p.extra_days).toFixed(1)},${Y(p.avg_review).toFixed(1)}`).join(" ");
    const area = `${line} L${X(shown[shown.length - 1].extra_days).toFixed(1)},${(pad.top + plotH).toFixed(1)} L${X(xMin).toFixed(1)},${(pad.top + plotH).toFixed(1)} Z`;

    const gridLines = [0, 0.25, 0.5, 0.75, 1].map((t) => {
      const y = pad.top + t * plotH;
      return `<line x1="${pad.left}" y1="${y}" x2="${width - pad.right}" y2="${y}" class="trap-gridline"/>`;
    }).join("");
    const xTicks = [0, 5, 10, 15, 20, 25, 30].filter((d) => d <= xMax).map((d) =>
      `<text x="${X(d).toFixed(1)}" y="${height - 14}" class="trap-axis-label" text-anchor="middle">+${d}</text>`).join("");
    const yTicks = [yMin + 0.03, (yMin + yMax) / 2, yMax - 0.03].map((v) =>
      `<text x="${pad.left - 7}" y="${(Y(v) + 3).toFixed(1)}" class="trap-axis-label" text-anchor="end">${v.toFixed(2)}</text>`).join("");

    const last = shown[shown.length - 1];
    svg.innerHTML = `
      ${gridLines}
      <path d="${area}" class="trap-area"/>
      <path d="${line}" class="trap-line"/>
      <circle cx="${X(last.extra_days).toFixed(1)}" cy="${Y(last.avg_review).toFixed(1)}" r="4.5" class="trap-dot"/>
      ${xTicks}${yTicks}
      <text x="${width / 2}" y="${height - 2}" class="trap-axis-title" text-anchor="middle">extra promise days (D)</text>
    `;
  }

  function setKpis(d) {
    const p = at(d);
    $("tck-review").textContent = fmt(p.avg_review, 2);
    $("tck-late").textContent = `${fmt(p.late_rate * 100, 1)}%`;
    $("tck-star").textContent = `${fmt(p.one_star_rate * 100, 1)}%`;
    $("tc-kpi-review").classList.toggle("good", p.avg_review >= trap.best_avg_review - 0.02);
    $("tc-kpi-late").classList.toggle("good", p.late_rate <= 0.005);
    $("tc-kpi-star").classList.toggle("good", p.one_star_rate <= curve[0].one_star_rate * 0.75);
  }

  function reset() {
    stage.classList.remove("desaturated");
    $("trap-alarm").hidden = true;
    $("refusal-overlay").hidden = true;
    $("refusal-overlay").classList.remove("on");
    status.textContent = "idle";
    status.className = "tc-status";
    slider.value = 0;
    $("tc-days").textContent = "+0";
    setKpis(0);
    ["tc-kpi-review", "tc-kpi-late", "tc-kpi-star"].forEach((id) => $(id).classList.remove("good"));
    drawChart(reducedMotion ? 1 : 0.04);
  }

  async function play() {
    if (playing) return;
    playing = true;
    reset();
    status.textContent = "maximizing reviews…";
    status.classList.add("running");

    if (!reducedMotion) {
      // the optimizer drags the slider — the metric only ever gets better
      const duration = 4600;
      const start = performance.now();
      await new Promise((resolve) => {
        const tick = (now) => {
          const t = Math.min((now - start) / duration, 1);
          const eased = t; // deliberate: linear, relentless
          const d = eased * maxDays;
          slider.value = d;
          $("tc-days").textContent = `+${Math.round(d)}`;
          setKpis(d);
          drawChart(eased);
          if (t < 1) requestAnimationFrame(tick);
          else resolve();
        };
        requestAnimationFrame(tick);
      });
    } else {
      slider.value = maxDays;
      $("tc-days").textContent = `+${maxDays}`;
      setKpis(maxDays);
      drawChart(1);
    }

    // nothing in the data ever says stop.
    status.textContent = "no optimum found";
    status.className = "tc-status alarm";
    $("trap-alarm").hidden = false;
    shake();
    stage.classList.add("desaturated");

    await sleep(reducedMotion ? 200 : 1400);

    // the interrupt — the one moment of personality
    const overlay = $("refusal-overlay");
    overlay.hidden = false;
    requestAnimationFrame(() => overlay.classList.add("on"));
    await sleep(reducedMotion ? 100 : 800);
    await typewriter($("refusal-line"),
      "I can prove padding wins. I won't recommend it.", { cps: 26 });
    await sleep(reducedMotion ? 300 : 2200);
    overlay.classList.remove("on");
    await sleep(500);
    overlay.hidden = true;
    stage.classList.remove("desaturated");
    playing = false;
  }

  $("trap-refusal-text").textContent = trap.why_we_refuse;
  $("trap-caveat-text").textContent = trap.caveat || "";
  reset();

  $("trap-replay").addEventListener("click", play);
  onInView($("stage-trap"), play, { threshold: 0.35 });
}
