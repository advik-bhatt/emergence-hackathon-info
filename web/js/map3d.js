// map3d.js — extruded Brazil, hover-raise states, schematic delivery arcs.
// Heights and colors are DATA (orders at risk / verdict); the arcs are labeled
// schematic because fixtures record destination-state outcomes, not routes.
import * as THREE from "three";
import { OrbitControls } from "../vendor/OrbitControls.js";
import { fmt, reducedMotion } from "./fx.js";

const CENTER = { lon: -54, lat: -14.5 };
const K = 1.05; // degrees → world units

const project = ([lon, lat]) => [(lon - CENTER.lon) * K, (lat - CENTER.lat) * K];

const COLORS = {
  FIX:  { base: 0x8f2e22, emissive: 0xd94f36 },
  PAD:  { base: 0x8a6b1f, emissive: 0xdca93f },
  KEEP: { base: 0x1f6b47, emissive: 0x3fae74 },
  NA:   { base: 0x232a30, emissive: 0x2c343b },
};

export async function initMap({ container, lanes, onSelect }) {
  const geo = await (await fetch("assets/brazil-states.min.json")).json();
  const byState = Object.fromEntries(lanes.map((l) => [l.state, l]));
  const maxRisk = Math.max(...lanes.map((l) => l.orders_at_risk), 1);

  // ── scene ──────────────────────────────────────────────────────
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x0a0f13, 55, 110);

  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 300);
  camera.position.set(4, 30, 34);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableZoom = false;
  controls.enablePan = false;
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.autoRotate = !reducedMotion;
  controls.autoRotateSpeed = 0.55;
  controls.minPolarAngle = 0.55;
  controls.maxPolarAngle = 1.25;
  controls.target.set(0, 0, 0);

  let idleTimer;
  renderer.domElement.addEventListener("pointerdown", () => {
    controls.autoRotate = false;
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => { controls.autoRotate = !reducedMotion; }, 4000);
  });

  // lights
  scene.add(new THREE.AmbientLight(0x8fb4c9, 0.75));
  const key = new THREE.DirectionalLight(0xd9f5ec, 1.4);
  key.position.set(-18, 34, 22);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x4f8fd9, 0.7);
  rim.position.set(24, 12, -20);
  scene.add(rim);

  // faint floor grid
  const grid = new THREE.GridHelper(160, 64, 0x1d3a33, 0x14222a);
  grid.material.transparent = true;
  grid.material.opacity = 0.35;
  grid.position.y = -0.06;
  scene.add(grid);

  // ── states ─────────────────────────────────────────────────────
  const stateGroup = new THREE.Group();
  scene.add(stateGroup);
  const meshes = [];
  const labels = [];
  const centroids = {};

  geo.features.forEach((feat, fi) => {
    const sigla = feat.properties.sigla;
    const lane = byState[sigla];
    const verdict = lane ? lane.verdict : "NA";
    const height = lane
      ? 0.35 + (lane.orders_at_risk / maxRisk) * 3.1
      : 0.12;
    const palette = COLORS[verdict] || COLORS.NA;

    const shapes = [];
    let cx = 0, cy = 0, cn = 0;
    const polys = feat.geometry.type === "MultiPolygon"
      ? feat.geometry.coordinates
      : [feat.geometry.coordinates];
    polys.forEach((poly) => {
      const [outer, ...holes] = poly;
      const shape = new THREE.Shape(outer.map((pt) => {
        const [x, y] = project(pt);
        cx += x; cy += y; cn++;
        return new THREE.Vector2(x, y);
      }));
      holes.forEach((ring) => {
        shape.holes.push(new THREE.Path(ring.map((pt) => new THREE.Vector2(...project(pt)))));
      });
      shapes.push(shape);
    });

    const geom = new THREE.ExtrudeGeometry(shapes, { depth: height, bevelEnabled: false });
    geom.rotateX(-Math.PI / 2); // extrusion now points +y; north → -z
    const mat = new THREE.MeshStandardMaterial({
      color: palette.base,
      emissive: palette.emissive,
      emissiveIntensity: lane ? 0.16 : 0.05,
      roughness: 0.55,
      metalness: 0.25,
      transparent: true,
      opacity: lane ? 0.96 : 0.8,
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.userData = { sigla, lane, height, baseEmissive: lane ? 0.16 : 0.05 };
    // intro: rise from the floor, west-to-east sweep
    mesh.scale.y = 0.001;
    mesh.userData.introDelay = 250 + fi * 42;
    stateGroup.add(mesh);
    meshes.push(mesh);

    // neon edge
    const edge = new THREE.LineSegments(
      new THREE.EdgesGeometry(geom, 24),
      new THREE.LineBasicMaterial({ color: 0x3d5e58, transparent: true, opacity: 0.5 }),
    );
    edge.scale.y = 0.001;
    mesh.userData.edge = edge;
    stateGroup.add(edge);

    const centroid = new THREE.Vector3(cx / cn, height + 0.4, -(cy / cn));
    centroids[sigla] = centroid;

    // DOM label
    const label = document.createElement("div");
    label.className = "state-label";
    label.textContent = sigla;
    if (!lane) label.style.opacity = "0.35";
    container.appendChild(label);
    labels.push({ el: label, sigla, pos: centroid, hasData: !!lane });
  });

  // ── schematic arcs + parcel particles ──────────────────────────
  const arcGroup = new THREE.Group();
  scene.add(arcGroup);
  const parcels = []; // { points, sprite, t, speed, late }
  const HUB = (centroids.SP || new THREE.Vector3()).clone().setY(0.3);

  function clearArcs() {
    arcGroup.clear();
    parcels.length = 0;
  }

  function fireArc(sigla, { persistent = false } = {}) {
    const end = centroids[sigla];
    const lane = byState[sigla];
    if (!end || !lane || sigla === "SP") return;
    const start = HUB.clone();
    const mid = start.clone().lerp(end, 0.5);
    mid.y += start.distanceTo(end) * 0.42;
    const curve = new THREE.QuadraticBezierCurve3(start, mid, end.clone());
    const pts = curve.getPoints(64);

    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({
        color: lane.verdict === "FIX" ? 0xd94f36 : 0x58c9a8,
        transparent: true,
        opacity: 0.42,
        blending: THREE.AdditiveBlending,
      }),
    );
    arcGroup.add(line);

    const n = 3;
    for (let i = 0; i < n; i++) {
      const late = Math.random() * 100 < lane.late_rate;
      const sprite = new THREE.Mesh(
        new THREE.SphereGeometry(0.16, 10, 10),
        new THREE.MeshBasicMaterial({ color: late ? 0xff6a50 : 0x7df5c0 }),
      );
      arcGroup.add(sprite);
      parcels.push({
        curve, sprite, late, persistent,
        t: i / n,
        speed: (0.0018 + Math.random() * 0.0012) * (late ? 0.55 : 1),
      });
    }
  }

  // ambient traffic on the worst lanes
  const worst = lanes.filter((l) => l.verdict === "FIX").slice(0, 4);
  worst.forEach((l) => fireArc(l.state, { persistent: true }));

  // ── picking ────────────────────────────────────────────────────
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  const tip = document.getElementById("map-tip");
  const tipState = document.getElementById("tip-state");
  const tipRows = document.getElementById("tip-rows");
  let hovered = null;
  let selected = null;

  function setTip(lane, x, y) {
    tipState.textContent = `${lane.state}`;
    tipRows.innerHTML = "";
    const rows = [
      ["orders", fmt(lane.orders)],
      ["promised", `${fmt(lane.current_promise, 1)}d`],
      ["median actual", `${fmt(lane.median_days, 1)}d`],
      ["p95 actual", `${fmt(lane.p95_days, 1)}d`],
      ["late rate", `${fmt(lane.late_rate, 1)}%`],
      ["order-days at risk", fmt(lane.orders_at_risk)],
    ];
    rows.forEach(([k, v]) => {
      const div = document.createElement("div");
      const b = document.createElement("b");
      b.textContent = v;
      div.append(`${k} `, b);
      tipRows.appendChild(div);
    });
    tip.hidden = false;
    tip.style.left = `${Math.min(x + 18, innerWidth - 240)}px`;
    tip.style.top = `${Math.min(y + 14, innerHeight - 220)}px`;
  }

  renderer.domElement.addEventListener("pointermove", (e) => {
    const r = renderer.domElement.getBoundingClientRect();
    pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1;
    pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(meshes, false)[0];
    const mesh = hit ? hit.object : null;

    if (hovered && hovered !== mesh) hovered = null;
    if (mesh && mesh.userData.lane) {
      hovered = mesh;
      setTip(mesh.userData.lane, e.clientX, e.clientY);
      renderer.domElement.style.cursor = "pointer";
    } else {
      tip.hidden = true;
      renderer.domElement.style.cursor = "";
    }
  });
  renderer.domElement.addEventListener("pointerleave", () => {
    hovered = null;
    tip.hidden = true;
  });

  renderer.domElement.addEventListener("click", () => {
    if (!hovered || !hovered.userData.lane) return;
    selectState(hovered.userData.sigla, { fire: true, notify: true });
  });

  function selectState(sigla, { fire = false, notify = false } = {}) {
    selected = meshes.find((m) => m.userData.sigla === sigla) || null;
    labels.forEach((l) => l.el.classList.toggle("sel", l.sigla === sigla));
    if (fire) {
      clearArcs();
      worst.forEach((l) => fireArc(l.state, { persistent: true }));
      fireArc(sigla);
    }
    if (notify && onSelect && byState[sigla]) onSelect(byState[sigla]);
  }

  // ── render loop ────────────────────────────────────────────────
  const clock = new THREE.Clock();
  let started = performance.now();

  function resize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }
  resize();
  addEventListener("resize", resize);

  const v = new THREE.Vector3();
  function animate() {
    requestAnimationFrame(animate);
    const t = clock.getElapsedTime();
    const now = performance.now();

    meshes.forEach((mesh) => {
      // intro rise
      const el = (now - started - mesh.userData.introDelay) / 900;
      if (el > 0 && mesh.scale.y < 1) {
        const k = Math.min(el, 1);
        const eased = 1 - Math.pow(1 - k, 4);
        mesh.scale.y = Math.max(eased, 0.001);
        mesh.userData.edge.scale.y = mesh.scale.y;
      }
      // hover / selection styling
      const isHover = mesh === hovered;
      const isSel = mesh === selected;
      const targetY = isHover ? 0.45 : 0;
      mesh.position.y += (targetY - mesh.position.y) * 0.18;
      mesh.userData.edge.position.y = mesh.position.y;
      const pulse = isSel ? 0.45 + Math.sin(t * 3.4) * 0.25 : 0;
      mesh.material.emissiveIntensity =
        mesh.userData.baseEmissive + (isHover ? 0.5 : 0) + pulse;
    });

    // parcels along arcs
    for (const p of parcels) {
      p.t += p.speed * (reducedMotion ? 0 : 1);
      if (p.t > 1) p.t = 0;
      p.curve.getPointAt(Math.min(p.t, 1), v);
      p.sprite.position.copy(v);
    }

    // project labels
    labels.forEach((l) => {
      v.copy(l.pos).applyMatrix4(stateGroup.matrixWorld);
      v.project(camera);
      const x = (v.x * 0.5 + 0.5) * container.clientWidth;
      const y = (-v.y * 0.5 + 0.5) * container.clientHeight;
      l.el.style.left = `${x}px`;
      l.el.style.top = `${y}px`;
      l.el.style.display = v.z < 1 ? "" : "none";
    });

    controls.update();
    renderer.render(scene, camera);
  }
  animate();

  return { selectState };
}
