// fx.js — shared effects toolkit. No dependencies.
export const $ = (id) => document.getElementById(id);

export const fmt = (n, digits = 0) =>
  Number(n).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

export async function getJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

export const reducedMotion =
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ── count-up odometer ────────────────────────────────────────────
export function countUp(el, target, { duration = 1200, digits = 0, prefix = "", suffix = "" } = {}) {
  if (reducedMotion) {
    el.textContent = prefix + fmt(target, digits) + suffix;
    return;
  }
  const start = performance.now();
  const from = 0;
  const tick = (now) => {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 4); // ease-out-quart
    el.textContent = prefix + fmt(from + (target - from) * eased, digits) + suffix;
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

// ── typewriter ───────────────────────────────────────────────────
export function typewriter(el, text, { cps = 55 } = {}) {
  if (reducedMotion) {
    el.textContent = text;
    return Promise.resolve();
  }
  el.textContent = "";
  return new Promise((resolve) => {
    let i = 0;
    const step = () => {
      // type 1-3 chars per frame-ish tick for a natural cadence
      i = Math.min(i + 1 + Math.floor(Math.random() * 2), text.length);
      el.textContent = text.slice(0, i);
      if (i < text.length) setTimeout(step, 1000 / cps);
      else resolve();
    };
    step();
  });
}

// ── word-by-word generate (LLM-stream feel) ──────────────────────
export function wordGenerate(el, text, { stagger = 42 } = {}) {
  el.innerHTML = "";
  text.split(/\s+/).forEach((word, i) => {
    const span = document.createElement("span");
    span.className = "w";
    span.textContent = word + " ";
    span.style.setProperty("--d", `${i * stagger}ms`);
    el.appendChild(span);
  });
}

// ── in-view trigger (fires once per arm) ────────────────────────
export function onInView(el, callback, { threshold = 0.35 } = {}) {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        io.disconnect();
        callback();
      }
    });
  }, { threshold });
  io.observe(el);
  return io;
}

// ── screen shake ─────────────────────────────────────────────────
export function shake() {
  if (reducedMotion) return;
  const app = $("app");
  app.classList.remove("shake");
  void app.offsetWidth;
  app.classList.add("shake");
}

// ── confetti (tiny, hand-rolled) ─────────────────────────────────
export function confetti({ count = 90, origin = { x: 0.5, y: 0.55 } } = {}) {
  if (reducedMotion) return;
  const canvas = $("confetti-canvas");
  const ctx = canvas.getContext("2d");
  canvas.width = innerWidth;
  canvas.height = innerHeight;
  const colors = ["#6ff0b4", "#f0d06f", "#7fd4f0", "#c9a2f5", "#f07f6f"];
  const parts = Array.from({ length: count }, () => ({
    x: origin.x * canvas.width,
    y: origin.y * canvas.height,
    vx: (Math.random() - 0.5) * 14,
    vy: -Math.random() * 13 - 4,
    w: 5 + Math.random() * 6,
    h: 3 + Math.random() * 4,
    rot: Math.random() * Math.PI,
    vr: (Math.random() - 0.5) * 0.3,
    color: colors[(Math.random() * colors.length) | 0],
    life: 1,
  }));
  let raf;
  const tick = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let alive = false;
    for (const p of parts) {
      p.vy += 0.35;
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.vr;
      p.life -= 0.008;
      if (p.life > 0 && p.y < canvas.height + 20) alive = true;
      ctx.save();
      ctx.globalAlpha = Math.max(p.life, 0);
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    }
    if (alive) raf = requestAnimationFrame(tick);
    else ctx.clearRect(0, 0, canvas.width, canvas.height);
  };
  cancelAnimationFrame(raf);
  tick();
}

// ── 3D tilt cards (Aceternity-style) ─────────────────────────────
export function initTilt(root = document) {
  if (reducedMotion || !matchMedia("(hover: hover) and (pointer: fine)").matches) return;
  root.querySelectorAll(".tilt").forEach((card) => {
    card.addEventListener("pointermove", (e) => {
      const r = card.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5;
      const py = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform =
        `perspective(700px) rotateY(${px * 10}deg) rotateX(${py * -10}deg) translateZ(4px)`;
    });
    card.addEventListener("pointerleave", () => {
      card.style.transform = "";
    });
  });
}

// ── glass cursor-glow tracking ───────────────────────────────────
export function initGlassGlow(root = document) {
  if (!matchMedia("(hover: hover) and (pointer: fine)").matches) return;
  root.querySelectorAll(".glass").forEach((el) => {
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      el.style.setProperty("--gx", `${((e.clientX - r.left) / r.width) * 100}%`);
      el.style.setProperty("--gy", `${((e.clientY - r.top) / r.height) * 100}%`);
    });
  });
}

// ── receipts: provenance popover on any [data-receipt] ───────────
export function initReceipts(receipts) {
  const pop = $("receipt-pop");
  const q = $("rp-q");
  const sql = $("rp-sql");
  let hideTimer;

  const show = (el, e) => {
    const slug = el.dataset.receipt;
    const rec = receipts[slug];
    if (!rec) return;
    q.textContent = `“${rec.nl_question}”`;
    sql.textContent = rec.sql.trim();
    pop.hidden = false;
    const pw = Math.min(560, innerWidth - 32);
    let x = Math.min(e.clientX + 16, innerWidth - pw - 16);
    let y = e.clientY + 18;
    if (y > innerHeight * 0.5) y = Math.max(16, e.clientY - pop.offsetHeight - 18);
    pop.style.left = `${Math.max(16, x)}px`;
    pop.style.top = `${y}px`;
  };

  document.querySelectorAll("[data-receipt]").forEach((el) => {
    el.addEventListener("pointerenter", (e) => {
      clearTimeout(hideTimer);
      hideTimer = setTimeout(() => show(el, e), 550);
    });
    el.addEventListener("pointerleave", () => {
      clearTimeout(hideTimer);
      pop.hidden = true;
    });
  });
}
