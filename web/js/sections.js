// sections.js — season calendar, the parcel race, the star wall, the ops queue.
import { $, fmt, countUp, onInView, confetti, reducedMotion } from "./fx.js";

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
const MONTH_FULL = ["January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December"];

// Brazilian retail moments worth a ribbon
const HOLIDAYS = {
  2: { label: "carnaval", hot: false },
  5: { label: "mães", hot: false },
  6: { label: "namorados", hot: false },
  11: { label: "black friday", hot: true },
  12: { label: "natal", hot: true },
};

/* ═══════════ SEASON CALENDAR ═══════════ */
export function initSeason(months, { onPickMonth } = {}) {
  const grid = $("season-grid");
  const byKey = {};
  months.forEach((m) => { byKey[`${m.order_year}-${m.order_month}`] = m; });
  const years = [...new Set(months.map((m) => m.order_year))].sort();
  const maxRate = Math.max(...months.map((m) => m.late_rate_pct));

  grid.innerHTML = "";

  // header row of month labels
  const head = document.createElement("div");
  head.className = "season-yrow";
  head.appendChild(document.createElement("span"));
  MONTHS.forEach((m) => {
    const s = document.createElement("span");
    s.className = "season-mlabel";
    s.textContent = m;
    head.appendChild(s);
  });
  grid.appendChild(head);

  let selectedCell = null;

  years.forEach((year) => {
    const row = document.createElement("div");
    row.className = "season-yrow";
    const yl = document.createElement("span");
    yl.className = "season-ylabel";
    yl.textContent = year;
    row.appendChild(yl);

    for (let m = 1; m <= 12; m++) {
      const cell = document.createElement("button");
      cell.className = "season-cell";
      const data = byKey[`${year}-${m}`];
      if (!data) {
        cell.classList.add("empty");
        cell.disabled = true;
        cell.setAttribute("aria-label", `${MONTH_FULL[m - 1]} ${year} — no data`);
      } else {
        const r = data.late_rate_pct / maxRate;
        cell.style.background =
          `oklch(${(0.26 + r * 0.2).toFixed(3)} ${(0.04 + r * 0.14).toFixed(3)} ${(152 - r * 126).toFixed(0)} / ${(0.45 + r * 0.5).toFixed(2)})`;
        cell.setAttribute("aria-label",
          `${MONTH_FULL[m - 1]} ${year}: ${fmt(data.num_orders)} orders, ${fmt(data.late_rate_pct, 1)}% late`);

        const rate = document.createElement("span");
        rate.className = "sc-rate";
        rate.textContent = `${fmt(data.late_rate_pct, 0)}%`;
        cell.appendChild(rate);

        cell.addEventListener("mouseenter", () => showDetail(data, year, m, months));
        cell.addEventListener("focus", () => showDetail(data, year, m, months));
        cell.addEventListener("click", () => {
          if (selectedCell) selectedCell.classList.remove("selected");
          selectedCell = cell;
          cell.classList.add("selected");
          onPickMonth?.(m, `${MONTH_FULL[m - 1]} ${year}`);
        });
      }
      const hol = HOLIDAYS[m];
      if (hol) {
        const ribbon = document.createElement("span");
        ribbon.className = "sc-holiday" + (hol.hot ? " hot" : "");
        ribbon.textContent = hol.label;
        cell.appendChild(ribbon);
      }
      row.appendChild(cell);
    }
    grid.appendChild(row);
  });

  return {
    clearSelection() {
      selectedCell?.classList.remove("selected");
      selectedCell = null;
    },
  };
}

function showDetail(data, year, month, months) {
  $("sd-kicker").textContent = `${data.num_orders >= 5000 ? "PEAK LOAD" : "RECORDED MONTH"}`;
  $("sd-title").textContent = `${MONTH_FULL[month - 1]} ${year}`;
  const rows = $("sd-rows");
  rows.innerHTML = "";

  const prev = months.find((m) =>
    (month === 1 && m.order_year === year - 1 && m.order_month === 12) ||
    (m.order_year === year && m.order_month === month - 1));

  const add = (k, v, cls) => {
    const div = document.createElement("div");
    div.className = "sd-row";
    const b = document.createElement("b");
    b.textContent = v;
    if (cls) b.className = cls;
    const span = document.createElement("span");
    span.textContent = k;
    div.append(span, b);
    rows.appendChild(div);
  };

  const volDelta = prev ? ((data.num_orders - prev.num_orders) / prev.num_orders) * 100 : null;
  add("orders", fmt(data.num_orders) + (volDelta != null ? `  (${volDelta >= 0 ? "+" : ""}${fmt(volDelta, 0)}%)` : ""));
  add("avg promised", `${fmt(data.avg_promised_days, 1)}d`);
  add("avg delivered", `${fmt(data.avg_actual_delivery_days, 1)}d`,
    data.avg_actual_delivery_days > data.avg_promised_days ? "bad" : "good");
  add("late rate", `${fmt(data.late_rate_pct, 1)}%`, data.late_rate_pct > 10 ? "bad" : "good");

  const punch = $("sd-punch");
  if (month === 11 && prev && data.avg_promised_days < prev.avg_promised_days) {
    punch.textContent = `Volume ${volDelta >= 0 ? "+" + fmt(volDelta, 0) : fmt(volDelta, 0)}% — and the promise got SHORTER. They made a harder promise exactly when they couldn't keep it.`;
  } else if (data.late_rate_pct > 15) {
    punch.textContent = "One in six promises broke this month.";
  } else if (data.late_rate_pct < 3) {
    punch.textContent = "A calm month — the network kept its word.";
  } else {
    punch.textContent = "";
  }
}

/* ═══════════ THE PARCEL RACE ═══════════ */
export function initRace() {
  const race = $("race");
  let currentLane = null;
  let raf = null;

  function layout(lane) {
    const maxDay = Math.ceil(lane.p95_days) + 3;
    const axis = $("race-axis");
    axis.innerHTML = "";
    const step = maxDay > 30 ? 10 : 5;
    for (let d = 0; d <= maxDay; d += step) {
      const i = document.createElement("i");
      i.style.left = `calc(40px + (100% - 80px) * ${d / maxDay})`;
      const b = document.createElement("b");
      b.textContent = `d${d}`;
      i.appendChild(b);
      axis.appendChild(i);
    }
    const flag = $("race-flag");
    flag.style.left = `calc(40px + (100% - 80px) * ${lane.current_promise / maxDay})`;
    $("flag-days").textContent = fmt(lane.current_promise, 0);
    return maxDay;
  }

  function run(lane) {
    cancelAnimationFrame(raf);
    currentLane = lane;
    const maxDay = layout(lane);
    const pMed = $("parcel-median");
    const pP95 = $("parcel-p95");
    const counter = $("race-counter");
    const broken = $("race-broken");
    pMed.className = "race-parcel";
    pP95.className = "race-parcel";
    broken.hidden = true;

    const pos = (day) => `calc(40px + (100% - 80px) * ${Math.min(day / maxDay, 1)})`;
    if (reducedMotion) {
      pMed.style.left = pos(lane.median_days);
      pP95.style.left = pos(lane.p95_days);
      pMed.classList.add("done");
      pP95.classList.add("late");
      counter.textContent = `day ${fmt(lane.p95_days, 0)}`;
      broken.hidden = lane.p95_days <= lane.current_promise;
      return;
    }

    const duration = 5200;
    const start = performance.now();
    let brokeShown = false;
    const tick = (now) => {
      const t = Math.min((now - start) / duration, 1);
      const day = t * maxDay;
      counter.textContent = `day ${Math.floor(day)}`;
      pMed.style.left = pos(Math.min(day, lane.median_days));
      pP95.style.left = pos(Math.min(day, lane.p95_days));
      if (day >= lane.median_days) pMed.classList.add("done");
      if (day > lane.current_promise && day < lane.p95_days) pP95.classList.add("late");
      if (!brokeShown && day > lane.current_promise && lane.p95_days > lane.current_promise) {
        broken.hidden = false;
        brokeShown = true;
      }
      if (day >= lane.p95_days) pP95.classList.replace("late", "late"); // stays red
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
  }

  $("race-replay").addEventListener("click", () => currentLane && run(currentLane));

  return {
    setLane(lane, { autorun = false } = {}) {
      currentLane = lane;
      layout(lane);
      if (autorun) run(lane);
    },
    run: () => currentLane && run(currentLane),
    arm(lane) {
      currentLane = lane;
      layout(lane);
      onInView($("stage-race"), () => run(currentLane));
    },
  };
}

/* ═══════════ STAR WALL ═══════════ */
export function initStars(reviewRows) {
  const wall = $("star-wall");
  wall.innerHTML = "";
  const cards = reviewRows.map((row) => {
    const [bucket, orders, avg, oneStar] = row;
    const card = document.createElement("div");
    card.className = "star-bucket";

    const label = document.createElement("div");
    label.className = "sb-label";
    label.textContent = bucket;
    card.appendChild(label);

    const stars = document.createElement("div");
    stars.className = "sb-stars";
    const kept = Math.round(avg);
    for (let i = 0; i < 5; i++) {
      const s = document.createElement("span");
      s.className = "sb-star";
      s.textContent = "★";
      if (i >= kept) {
        s.dataset.lost = "1";
        s.style.setProperty("--d", `${(i - kept) * 160 + 200}ms`);
      }
      stars.appendChild(s);
    }
    card.appendChild(stars);

    const score = document.createElement("div");
    score.className = "sb-score";
    score.textContent = "0.00";
    card.appendChild(score);

    const one = document.createElement("div");
    one.className = "sb-onestar";
    const b = document.createElement("b");
    b.textContent = `${fmt(oneStar, 1)}%`;
    one.append(b, " leave 1 star");
    card.appendChild(one);

    wall.appendChild(card);
    return { card, avg, orders };
  });

  onInView(wall, () => {
    cards.forEach(({ card, avg }, ci) => {
      setTimeout(() => {
        countUp(card.querySelector(".sb-score"), avg, { digits: 2, duration: 1000 });
        card.querySelectorAll('[data-lost="1"]').forEach((s) => s.classList.add("lost"));
      }, ci * 220);
    });
  });
}

/* ═══════════ OPS QUEUE ═══════════ */
export function initQueue(lanes) {
  const list = $("queue");
  list.innerHTML = "";
  const maxRisk = Math.max(...lanes.map((l) => l.orders_at_risk), 1);

  const rows = lanes.map((lane, idx) => {
    const li = document.createElement("li");
    li.className = `queue-row ${lane.verdict.toLowerCase()}`;
    if (idx === 0) li.classList.add("boss");

    const rank = document.createElement("span");
    rank.className = "q-rank";
    rank.textContent = `#${idx + 1}`;
    li.appendChild(rank);

    const state = document.createElement("span");
    state.className = "q-state";
    state.textContent = lane.state;
    li.appendChild(state);

    const barWrap = document.createElement("div");
    barWrap.className = "q-bar-wrap";
    const bar = document.createElement("div");
    bar.className = "q-bar";
    bar.style.setProperty("--w", Math.max(lane.orders_at_risk / maxRisk, 0.02).toFixed(3));
    const barLabel = document.createElement("span");
    barLabel.className = "q-bar-label";
    barLabel.textContent =
      `promised ${fmt(lane.current_promise, 0)}d · p95 ${fmt(lane.p95_days, 0)}d · gap ${lane.gap >= 0 ? "+" : ""}${fmt(lane.gap, 1)}d · ${fmt(lane.late_rate, 1)}% late`;
    barWrap.append(bar, barLabel);
    li.appendChild(barWrap);

    const risk = document.createElement("span");
    risk.className = "q-risk";
    const riskN = document.createElement("span");
    riskN.textContent = "0";
    const riskL = document.createElement("small");
    riskL.textContent = "order-days at risk";
    risk.append(riskN, riskL);
    li.appendChild(risk);

    const chipWrap = document.createElement("span");
    const chip = document.createElement("span");
    chip.className = `verdict-chip ${lane.verdict.toLowerCase()}`;
    chip.textContent = lane.verdict;
    chipWrap.appendChild(chip);
    if (lane.is_borderline) {
      const bm = document.createElement("span");
      bm.className = "borderline-mark";
      bm.textContent = "borderline";
      chipWrap.appendChild(bm);
    }
    li.appendChild(chipWrap);

    list.appendChild(li);
    return { li, riskN, lane };
  });

  onInView(list, () => {
    rows.forEach(({ li, riskN, lane }, i) => {
      setTimeout(() => {
        li.classList.add("on");
        countUp(riskN, lane.orders_at_risk, { duration: 1100 });
      }, i * 110);
    });
    const keeps = lanes.filter((l) => l.verdict === "KEEP");
    if (keeps.length) {
      setTimeout(() => {
        $("queue-celebrate").hidden = false;
        confetti({ count: 60, origin: { x: 0.5, y: 0.85 } });
      }, rows.length * 110 + 700);
    }
  }, { threshold: 0.2 });
}
