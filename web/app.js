"use strict";

/* ============================================================
   Helpers
   ============================================================ */

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

const natural = (a, b) =>
  String(a).localeCompare(String(b), undefined, { numeric: true });
const greek = (a) => (/^a\d+$/.test(a) ? "α" + a.slice(1) : String(a));
const fmt = (set) =>
  [...set].length ? "{" + [...set].sort(natural).map(greek).join(", ") + "}" : "∅";
const sup = (n) => String(n).replace(/\d/g, (d) => "⁰¹²³⁴⁵⁶⁷⁸⁹"[d]);
const pct = (x, digits = 1) => (100 * x).toFixed(digits) + "%";
const num = (x) => Number(x).toLocaleString("en-US");
const tick = () => new Promise((r) => setTimeout(r, 0));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c != null && c !== false) node.append(c instanceof Node ? c : String(c));
  }
  return node;
}

const COLORS = {
  in: "#6fcf97",
  out: "#eb7070",
  undec: "#6b7079",
  edge: "#3a3d44",
  edgeLive: "#8b9099",
  text: "#e7e8ea",
};

/* ============================================================
   Python runtime
   ============================================================ */

const PY_FILES = [
  "argumentation/__init__.py",
  "argumentation/acceptance.py",
  "argumentation/examples.py",
  "argumentation/framework.py",
  "argumentation/labelling.py",
  "argumentation/semantics.py",
  "argumentation/strategic.py",
  "experiments/__init__.py",
  "experiments/run_experiments.py",
];

let pyCall = null;

async function bootPython() {
  try {
    const py = await loadPyodide();
    $("#loading-text").textContent = "Loading the argumentation library";
    const home = "/home/pyodide/";
    for (const path of PY_FILES) {
      const src = await fetch("../" + path).then((r) => {
        if (!r.ok) throw new Error(`could not load ${path}`);
        return r.text();
      });
      py.FS.mkdirTree(home + path.split("/").slice(0, -1).join("/"));
      py.FS.writeFile(home + path, src);
    }
    py.FS.writeFile(home + "bridge.py", await fetch("bridge.py").then((r) => r.text()));
    py.runPython(`import sys; sys.path.insert(0, "${home}")\nimport bridge`);
    pyCall = py.globals.get("bridge").call;
    $("#loading").classList.add("done");
    document.body.classList.add("py-ready");
    return true;
  } catch (err) {
    console.error(err);
    $("#loading-text").textContent =
      "Could not start Python. Serve the repository root over HTTP (see web/README) and reload.";
    return false;
  }
}

function call(name, payload) {
  return JSON.parse(pyCall(name, JSON.stringify(payload)));
}

/* ============================================================
   Graph rendering (shared)
   ============================================================ */

function graphStyle() {
  return [
    {
      selector: "node",
      style: {
        width: 46,
        height: 46,
        "background-color": "#131417",
        "border-width": 1.5,
        "border-color": COLORS.undec,
        label: "data(label)",
        color: COLORS.text,
        "font-family": "JetBrains Mono, ui-monospace, monospace",
        "font-size": 13,
        "text-valign": "center",
        "text-halign": "center",
        "overlay-opacity": 0,
        "transition-property": "border-color, background-color, background-opacity, opacity",
        "transition-duration": "180ms",
      },
    },
    { selector: "node.in", style: { "border-color": COLORS.in, "background-color": COLORS.in, "background-opacity": 0.16 } },
    { selector: "node.out", style: { "border-color": COLORS.out, "background-color": COLORS.out, "background-opacity": 0.1 } },
    { selector: "node.undec", style: { "border-color": COLORS.undec } },
    { selector: 'node[agent = "y"]', style: { shape: "round-rectangle", width: 44, height: 40 } },
    { selector: 'node[agent = "z"]', style: { shape: "round-diamond", width: 56, height: 56 } },
    {
      selector: "node.source, node.member, node.hover",
      style: {
        "underlay-color": COLORS.text,
        "underlay-opacity": 0.14,
        "underlay-padding": 7,
        "underlay-shape": "ellipse",
      },
    },
    { selector: "node.member", style: { "underlay-opacity": 0.22, "border-width": 2.5 } },
    { selector: "node.hidden", style: { "border-style": "dashed", opacity: 0.38, "background-opacity": 0 } },
    {
      selector: "edge",
      style: {
        width: 1.4,
        "line-color": COLORS.edge,
        "target-arrow-color": COLORS.edge,
        "target-arrow-shape": "triangle",
        "arrow-scale": 0.9,
        "curve-style": "bezier",
        "control-point-step-size": 34,
        "overlay-opacity": 0,
        "transition-property": "line-color, target-arrow-color, opacity",
        "transition-duration": "180ms",
      },
    },
    { selector: "edge.live", style: { "line-color": COLORS.edgeLive, "target-arrow-color": COLORS.edgeLive } },
    { selector: "edge:loop", style: { "loop-direction": "-30deg", "loop-sweep": "50deg", "control-point-step-size": 56 } },
    { selector: "edge.chosen", style: { "line-color": COLORS.text, "target-arrow-color": COLORS.text, width: 2 } },
    { selector: "edge.hidden", style: { opacity: 0.14, "line-style": "dashed" } },
  ];
}

function makeGraph(container) {
  return cytoscape({
    container,
    style: graphStyle(),
    minZoom: 0.3,
    maxZoom: 1.3,
    wheelSensitivity: 0.2,
    autounselectify: true,
    boxSelectionEnabled: false,
  });
}

function setElements(cy, nodes, edges, positions) {
  cy.elements().remove();
  cy.add([
    ...nodes.map((n) => ({
      group: "nodes",
      data: { id: n.id, label: greek(n.id), agent: n.agent || "" },
      position: positions && positions[n.id] ? { ...positions[n.id] } : undefined,
    })),
    ...edges.map(([s, t]) => ({ group: "edges", data: { id: `${s}->${t}`, source: s, target: t } })),
  ]);
  if (positions && nodes.every((n) => positions[n.id])) {
    cy.scratch("base", positions);
    fitGraph(cy);
  } else {
    cy.scratch("base", null);
    cy.layout({ name: "circle", fit: false, sort: (a, b) => natural(a.id(), b.id()) }).run();
    fitGraph(cy);
  }
}

/* Fit the graph to its stage. Hand-placed presets are laid out wide, so on a
   tall, narrow stage (phones) they are turned on their side to stay readable. */
function fitGraph(cy) {
  const w = cy.width(), h = cy.height();
  if (!w || !h) return;
  const base = cy.scratch("base");
  if (base) {
    const xs = Object.values(base).map((p) => p.x), ys = Object.values(base).map((p) => p.y);
    const bw = Math.max(...xs) - Math.min(...xs), bh = Math.max(...ys) - Math.min(...ys);
    const flip = h > w * 1.1 && bw > bh * 1.3;
    cy.nodes().forEach((n) => {
      const p = base[n.id()];
      if (p) n.position(flip ? { x: -p.y, y: p.x } : { ...p });
    });
  }
  cy.fit(undefined, Math.round(Math.max(24, Math.min(90, Math.min(w, h) * 0.12))));
}

function applyLabelling(cy, labelling) {
  cy.batch(() => {
    cy.nodes().forEach((n) => {
      n.removeClass("in out undec");
      const lab = labelling && labelling[n.id()];
      if (lab) n.addClass(lab);
    });
    cy.edges().forEach((e) => {
      e.toggleClass("live", !!labelling && labelling[e.source().id()] === "in");
    });
  });
}

function tidy(cy) {
  cy.scratch("base", null);
  cy.layout({
    name: "cose",
    animate: true,
    animationDuration: 400,
    randomize: false,
    fit: true,
    padding: Math.round(Math.max(24, Math.min(90, Math.min(cy.width(), cy.height()) * 0.12))),
    nodeRepulsion: () => 90000,
    idealEdgeLength: () => 110,
  }).run();
}

/* ============================================================
   Playground
   ============================================================ */

const PG_PRESETS = {
  fig51: {
    args: ["a1", "a2", "a3", "a4", "a5"],
    attacks: [["a2", "a1"], ["a4", "a1"], ["a3", "a2"], ["a5", "a4"]],
    pos: { a3: { x: -260, y: 0 }, a2: { x: -130, y: 0 }, a1: { x: 0, y: 0 }, a4: { x: 130, y: 0 }, a5: { x: 260, y: 0 } },
    hint: "α3 and α5 are unattacked, so they are in from the start. Together they defend α1.",
  },
  fig52: {
    args: ["a1", "a2", "a3"],
    attacks: [["a1", "a2"], ["a2", "a1"]],
    pos: { a1: { x: -90, y: -40 }, a2: { x: 90, y: -40 }, a3: { x: 0, y: 100 } },
    hint: "α1 and α2 attack each other. Grounded stays undecided about both; preferred picks a side.",
  },
  edge: {
    args: ["a", "b", "c", "x", "y", "z"],
    attacks: [["a", "b"], ["b", "a"], ["b", "c"], ["c", "c"], ["x", "y"], ["y", "z"], ["z", "x"]],
    pos: {
      a: { x: -300, y: 0 }, b: { x: -170, y: 0 }, c: { x: -40, y: 0 },
      x: { x: 160, y: -80 }, y: { x: 260, y: 70 }, z: { x: 70, y: 70 },
    },
    hint: "The 3-cycle rules out any stable extension. Semi-stable prefers {b}: it also defeats c.",
  },
  cycle: {
    args: ["g", "u", "v", "w", "t"],
    attacks: [["g", "u"], ["u", "v"], ["v", "w"], ["w", "u"], ["u", "t"]],
    pos: { g: { x: -240, y: 0 }, u: { x: -90, y: 0 }, v: { x: 40, y: -95 }, w: { x: 40, y: 95 }, t: { x: -90, y: 150 } },
    hint: "Simple path g→u→t has even length; the walk g→u→v→w→u→t is odd. Used by Theorem 5.4.",
  },
  empty: { args: [], attacks: [], pos: {}, hint: "" },
};

const SEM_NAMES = {
  grounded: "Grounded",
  complete: "Complete",
  preferred: "Preferred",
  stable: "Stable",
  "semi-stable": "Semi-stable",
};

const pg = {
  cy: null,
  args: [],
  attacks: [],
  semantics: "grounded",
  mode: "edit",
  ext: 0,
  result: null,
  members: new Set(),
  step: null,
  playToken: 0,
  source: null,
  chosenEdge: null,
};

function pgLoad(key) {
  const p = PG_PRESETS[key];
  pg.args = [...p.args];
  pg.attacks = p.attacks.map((a) => [...a]);
  pg.members.clear();
  pg.source = pg.chosenEdge = null;
  pg.ext = 0;
  $("#pg-preset").value = key;
  $("#pg-hint").textContent = p.hint;
  setElements(pg.cy, pg.args.map((id) => ({ id })), pg.attacks, p.pos);
  pgUpdate();
}

function pgUpdate() {
  pgStop();
  if (!pyCall) return;
  pg.result = call("analyse", { arguments: pg.args, attacks: pg.attacks, semantics: pg.semantics });
  pg.ext = Math.min(pg.ext, Math.max(0, pg.result.extensions.length - 1));
  pgRender();
}

function pgCurrentLabelling() {
  const r = pg.result;
  if (!r) return null;
  if (pg.step != null) return r.steps[pg.step].labelling;
  return r.labellings[pg.ext] || null;
}

function pgRender() {
  const r = pg.result;
  if (!r) return;
  applyLabelling(pg.cy, pgCurrentLabelling());
  pg.cy.nodes().forEach((n) => n.toggleClass("member", pg.members.has(n.id())));

  // Extensions
  const exts = r.extensions;
  const name = SEM_NAMES[pg.semantics];
  $("#pg-ext-title").textContent =
    pg.semantics === "grounded" ? "Grounded extension" : `${name} extensions · ${exts.length}`;
  const list = $("#pg-extensions");
  list.replaceChildren();
  if (!exts.length) {
    list.append(el("div", { class: "muted" }, `No ${name.toLowerCase()} extension exists.`));
  }
  exts.forEach((e, i) => {
    list.append(
      el(
        "button",
        {
          class: "item" + (i === pg.ext && pg.step == null ? " active" : ""),
          onclick: () => { pgStop(); pg.ext = i; pgRender(); },
        },
        el("span", { class: "set" }, fmt(e)),
        el("span", { class: "faint mono" }, exts.length > 1 ? `E${i + 1}` : "")
      )
    );
  });

  const stepper = $("#pg-stepper");
  stepper.style.visibility = exts.length > 1 ? "visible" : "hidden";
  $("#pg-ext-count").textContent = `${pg.ext + 1} / ${exts.length}`;

  // F iteration (grounded only)
  $("#pg-steps-group").hidden = pg.semantics !== "grounded" || !pg.args.length;
  const steps = $("#pg-steps");
  steps.replaceChildren();
  const distinct = r.steps.filter((s) => !s.fixed);
  if (!distinct.length) distinct.push(r.steps[r.steps.length - 1]);
  distinct.forEach((s, i) => {
    const cls =
      pg.step == null ? "" : i === pg.step ? " current" : i > pg.step ? " pending" : "";
    steps.append(
      el(
        "button",
        { class: "item" + cls, onclick: () => { pgStop(); pg.step = i; pgRender(); } },
        el("span", { class: "k" }, `F${sup(i + 1)}(∅)`),
        el("span", { class: "set" }, fmt(s.set))
      )
    );
  });
  steps.append(
    el("div", { class: "faint", style: "font-size:12.5px" },
      `F${sup(distinct.length + 1)}(∅) = F${sup(distinct.length)}(∅): fixed point reached`)
  );

  // Acceptance status
  const statusList = $("#pg-status");
  statusList.replaceChildren();
  const tagClass = { "skeptically accepted": "in", "credulously accepted": "mid", rejected: "out" };
  const tagText = { "skeptically accepted": "skeptical", "credulously accepted": "credulous", rejected: "rejected" };
  Object.keys(r.status).sort(natural).forEach((a) => {
    statusList.append(
      el("div", { class: "status-row" },
        el("span", { class: "mono" }, greek(a)),
        el("span", { class: "tag " + tagClass[r.status[a]] }, tagText[r.status[a]]))
    );
  });
  if (!pg.args.length) statusList.append(el("div", { class: "muted" }, "No arguments yet."));
  $("#pg-status-hint").textContent =
    pg.semantics === "grounded"
      ? "With one extension, accepted arguments are accepted skeptically."
      : "Skeptical: in every extension. Credulous: in at least one.";

  // Set S checks
  $("#pg-set-group").hidden = pg.mode !== "pick";
  if (pg.mode === "pick") {
    const members = [...pg.members];
    $("#pg-set").textContent = "S = " + fmt(members);
    const c = call("check_set", { arguments: pg.args, attacks: pg.attacks, members });
    const yn = (v) => el("span", { class: v ? "yes" : "no" }, v ? "yes" : "no");
    $("#pg-set-checks").replaceChildren(
      el("div", { class: "check" }, el("span", {}, "Conflict-free"), yn(c.conflict_free)),
      el("div", { class: "check" }, el("span", {}, "Admissible"), yn(c.admissible)),
      el("div", { class: "check" }, el("span", {}, "Complete"), yn(c.complete)),
      el("div", { class: "check" }, el("span", {}, "F(S), what S defends"), el("span", { class: "set" }, fmt(c.characteristic))),
      el("div", { class: "check" }, el("span", {}, "S⁺, what S attacks"), el("span", { class: "set" }, fmt(c.plus)))
    );
  }
}

function pgStop() {
  pg.playToken++;
  pg.step = null;
  $("#pg-play").textContent = "Play";
}

async function pgPlay() {
  if (pg.step != null && $("#pg-play").textContent === "Stop") {
    pgStop();
    pgRender();
    return;
  }
  pgStop();
  const token = pg.playToken;
  $("#pg-play").textContent = "Stop";
  const n = Math.max(1, pg.result.steps.filter((s) => !s.fixed).length);
  // Start from all undecided, then reveal each F^i(∅).
  applyLabelling(pg.cy, Object.fromEntries(pg.args.map((a) => [a, "undec"])));
  await sleep(500);
  for (let i = 0; i < n; i++) {
    if (token !== pg.playToken) return;
    pg.step = i;
    pgRender();
    $("#pg-play").textContent = "Stop";
    await sleep(1100);
  }
  if (token !== pg.playToken) return;
  pgStop();
  pgRender();
}

function pgNextId() {
  for (let i = 1; ; i++) if (!pg.args.includes(`a${i}`)) return `a${i}`;
}

function pgClearPick() {
  if (pg.source) pg.cy.$id(pg.source).removeClass("source");
  if (pg.chosenEdge) pg.cy.$id(pg.chosenEdge).removeClass("chosen");
  pg.source = pg.chosenEdge = null;
}

function pgToggleAttack(s, t) {
  const i = pg.attacks.findIndex(([a, b]) => a === s && b === t);
  if (i >= 0) {
    pg.attacks.splice(i, 1);
    pg.cy.$id(`${s}->${t}`).remove();
  } else {
    pg.attacks.push([s, t]);
    pg.cy.add({ group: "edges", data: { id: `${s}->${t}`, source: s, target: t } });
  }
}

function pgDeleteSelection() {
  if (pg.source) {
    const id = pg.source;
    pg.args = pg.args.filter((a) => a !== id);
    pg.attacks = pg.attacks.filter(([a, b]) => a !== id && b !== id);
    pg.members.delete(id);
    pg.cy.$id(id).remove();
  } else if (pg.chosenEdge) {
    const [s, t] = pg.chosenEdge.split("->");
    pgToggleAttack(s, t);
  } else return;
  pg.source = pg.chosenEdge = null;
  pgUpdate();
}

function pgSetMode(mode) {
  pg.mode = mode;
  pgClearPick();
  $$("#pg-mode button").forEach((b) => b.classList.toggle("active", b.dataset.m === mode));
  $("#pg-mode-hint").textContent =
    mode === "edit"
      ? "Click empty space to add an argument. Click one argument, then another, to add an attack. Double-click for a self-attack. Select and press Delete to remove."
      : "Click arguments to put them in S. The checks on the right update as you go.";
  pgRender();
}

function initPlayground() {
  pg.cy = makeGraph($("#pg-graph"));
  const cy = pg.cy;

  cy.on("tap", (e) => {
    if (pg.mode !== "edit" || e.target !== cy) return;
    pgClearPick();
    cy.scratch("base", null);
    const id = pgNextId();
    pg.args.push(id);
    cy.add({ group: "nodes", data: { id, label: greek(id), agent: "" }, position: { ...e.position } });
    pgUpdate();
  });

  cy.on("tap", "node", (e) => {
    const id = e.target.id();
    if (pg.mode === "pick") {
      pg.members.has(id) ? pg.members.delete(id) : pg.members.add(id);
      pgRender();
      return;
    }
    if (pg.chosenEdge) pgClearPick();
    if (!pg.source) {
      pg.source = id;
      e.target.addClass("source");
    } else if (pg.source === id) {
      pgClearPick();
    } else {
      const s = pg.source;
      pgClearPick();
      pgToggleAttack(s, id);
      pgUpdate();
    }
  });

  cy.on("dragfree", "node", () => cy.scratch("base", null));

  cy.on("dbltap", "node", (e) => {
    if (pg.mode !== "edit") return;
    pgClearPick();
    pgToggleAttack(e.target.id(), e.target.id());
    pgUpdate();
  });

  cy.on("tap", "edge", (e) => {
    if (pg.mode !== "edit") return;
    const id = e.target.id();
    const same = pg.chosenEdge === id;
    pgClearPick();
    if (!same) {
      pg.chosenEdge = id;
      e.target.addClass("chosen");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (currentView !== "playground" || pg.mode !== "edit") return;
    if (["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName)) return;
    if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      pgDeleteSelection();
    } else if (e.key === "Escape") pgClearPick();
  });

  $("#pg-preset").addEventListener("change", (e) => pgLoad(e.target.value));
  $$("#pg-semantics button").forEach((b) =>
    b.addEventListener("click", () => {
      pg.semantics = b.dataset.s;
      pg.ext = 0;
      $$("#pg-semantics button").forEach((x) => x.classList.toggle("active", x === b));
      pgUpdate();
    })
  );
  $$("#pg-mode button").forEach((b) => b.addEventListener("click", () => pgSetMode(b.dataset.m)));
  $("#pg-layout").addEventListener("click", () => tidy(cy));
  $("#pg-clear").addEventListener("click", () => pgLoad("empty"));
  $("#pg-play").addEventListener("click", pgPlay);
  const stepExt = (d) => {
    const n = pg.result?.extensions.length || 0;
    if (n < 2) return;
    pgStop();
    pg.ext = (pg.ext + d + n) % n;
    pgRender();
  };
  $("#pg-prev").addEventListener("click", () => stepExt(-1));
  $("#pg-next").addEventListener("click", () => stepExt(1));
}

/* ============================================================
   Strategic game
   ============================================================ */

const AGENTS = ["x", "y", "z"];

const GAME_PRESETS = {
  ex510: {
    attacks: [["a1", "a2"], ["a2", "a3"], ["a3", "a4"], ["a3", "a5"]],
    types: { x: ["a1", "a4", "a5"], y: ["a2"], z: ["a3"] },
    pos: { a1: { x: -300, y: 0 }, a2: { x: -170, y: 0 }, a3: { x: -40, y: 0 }, a4: { x: 100, y: -75 }, a5: { x: 100, y: 75 } },
    note:
      "<b>Try hiding α1.</b> With α1 gone, α2 is unattacked and defeats α3, which frees α4 and α5. x goes from 1 accepted argument to 2.<br><br><span class='faint'>Errata: the book gives y and z each other's utilities. y holds α2 and gets 0; z holds α3 and gets 1.</span>",
  },
  ex511: {
    attacks: [["a1", "a2"], ["a2", "a3"], ["a3", "a4"], ["a3", "a5"], ["a6", "a3"]],
    types: { x: ["a1", "a4", "a5", "a6"], y: ["a2"], z: ["a3"] },
    pos: {
      a1: { x: -300, y: 0 }, a2: { x: -170, y: 0 }, a3: { x: -40, y: 0 },
      a4: { x: 100, y: -75 }, a5: { x: 100, y: 75 }, a6: { x: -40, y: -140 },
    },
    note:
      "<b>Truth wins.</b> α6 also attacks α3, so x gets all four arguments by revealing everything. The Theorem 5.4 condition still fails (α1 ↪ α4), so the condition is sufficient but not necessary.<br><br><span class='faint'>Errata: the book says α5 cancels the self-defeat; it is α6, which attacks α3.</span>",
  },
};

const Q3_TEXT = {
  rescue_costs_as_much: {
    title: "Rescue costs as much",
    body: "Hiding can get a rejected own argument accepted, but every such move loses at least as many own arguments. Utility counts arguments, so a one-for-one swap is never a strict gain.",
  },
  never_rescues: {
    title: "Never rescues",
    body: "Whatever the others reveal, hiding never turns a rejected own argument into an accepted one. The odd path is always cancelled by an even one, as α6 does in Example 5.11.",
  },
  self_cycles_only: {
    title: "Self-cycles only",
    body: "The only violations are α ↪ α: an odd cycle back to the same argument. Hiding an argument cannot make that same argument accepted.",
  },
};

const game = {
  cy: null,
  key: "ex510",
  attacks: [],
  types: {},
  reports: {},
  args: [],
  thm: null,
  brAgent: "x",
  saved: {},
  note: "",
  seed: 1,
};

function gameLoad(key, instance) {
  game.key = key;
  let pos = null;
  if (GAME_PRESETS[key]) {
    const p = GAME_PRESETS[key];
    game.attacks = p.attacks.map((a) => [...a]);
    game.types = structuredClone(p.types);
    pos = p.pos;
    game.note = p.note;
  } else {
    game.attacks = instance.attacks.map((a) => [...a]);
    game.types = structuredClone(instance.types);
    game.note = null;
  }
  for (const a of AGENTS) game.types[a] ??= [];
  game.args = AGENTS.flatMap((a) => game.types[a]).sort(natural);
  game.reports = structuredClone(game.types);
  $("#g-preset").value = key;
  $("#g-random").hidden = key !== "random";
  $("#g-br-out").textContent = "";

  const owner = {};
  for (const a of AGENTS) for (const arg of game.types[a]) owner[arg] = a;
  setElements(game.cy, game.args.map((id) => ({ id, agent: owner[id] })), game.attacks, pos);

  if (!pyCall) return;
  game.thm = call("theorems", { attacks: game.attacks, types: game.types });
  if (!game.note) game.note = gameAutoNote();
  gameRender();
}

function gameRoll() {
  game.seed = Math.floor(Math.random() * 1e9);
  const inst = call("random_instance", { p: Number($("#g-p").value), seed: game.seed });
  gameLoad("random", inst);
}

function gameAutoNote() {
  const t = game.thm;
  if (!t.strategyproof) {
    const m = t.manipulation;
    return `<b>Not strategyproof.</b> Agent ${m.agent} gains by hiding ${fmt(m.hidden)} (utility ${m.truthful_utility} → ${m.manipulated_utility}) when the others reveal ${Object.entries(m.others).map(([a, r]) => `${a}: ${fmt(r)}`).join(", ")}. Press <i>Show a manipulation</i> to play it.`;
  }
  if (!t.violations_walk.length) {
    return "<b>Strategyproof, guaranteed.</b> No agent holds two arguments joined by an odd path, so Theorem 5.4 applies and truth-telling is always a best response.";
  }
  const q = Q3_TEXT[t.q3_reason];
  return `<b>Strategyproof, although the condition fails.</b> Reason: <i>${q.title.toLowerCase()}</i>. ${q.body}`;
}

function gameRender() {
  const s = call("game_state", { attacks: game.attacks, types: game.types, reports: game.reports });
  const revealed = new Set(AGENTS.flatMap((a) => game.reports[a]));

  // Graph (chips are rebuilt below, so a pending mouseleave never fires)
  applyLabelling(game.cy, s.labelling);
  game.cy.batch(() => {
    game.cy.nodes().removeClass("hover");
    game.cy.nodes().forEach((n) => n.toggleClass("hidden", !revealed.has(n.id())));
    game.cy.edges().forEach((e) =>
      e.toggleClass("hidden", !revealed.has(e.source().id()) || !revealed.has(e.target().id()))
    );
  });

  // Agents
  const box = $("#g-agents");
  box.replaceChildren();
  for (const a of AGENTS) {
    const chips = game.types[a].map((arg) => {
      const shown = game.reports[a].includes(arg);
      const lab = shown ? s.labelling[arg] : null;
      return el(
        "button",
        {
          class: "chip" + (shown ? "" : " hidden") + (lab === "in" ? " in" : lab === "out" ? " out" : ""),
          title: shown ? "Click to hide" : "Click to reveal",
          onclick: () => gameToggle(a, arg),
          onmouseenter: () => game.cy.$id(arg).addClass("hover"),
          onmouseleave: () => game.cy.$id(arg).removeClass("hover"),
        },
        greek(arg)
      );
    });
    const hidden = game.types[a].length - game.reports[a].length;
    box.append(
      el("div", { class: "agent" },
        el("div", { class: "agent-head" },
          el("span", { class: "agent-name" }, el("span", { class: "shape " + a }), `Agent ${a}`),
          el("span", { class: "faint", style: "font-size:12px" },
            game.types[a].length ? (hidden ? `hiding ${hidden}` : "truthful") : "")),
        chips.length ? el("div", { class: "chips" }, chips) : el("div", { class: "empty" }, "No arguments"))
    );
  }

  // Outcome
  $("#g-outcome").textContent = fmt(s.outcome);
  const same = s.outcome.join() === s.truthful_outcome.join();
  $("#g-outcome-sub").textContent = same
    ? "Same as when everyone tells the truth"
    : `Truthful outcome would be ${fmt(s.truthful_outcome)}`;

  // Utilities
  const tbody = $("#g-util");
  tbody.replaceChildren();
  for (const a of AGENTS) {
    const u = s.utilities[a];
    const d = u.now - u.truthful;
    tbody.append(
      el("tr", {},
        el("td", {}, el("span", { class: "agent-name" }, el("span", { class: "shape " + a }), a)),
        el("td", {}, `${u.truthful} / ${game.types[a].length}`),
        el("td", {}, `${u.now}`),
        el("td", { class: "delta" + (d > 0 ? " up" : d < 0 ? " down" : "") }, d > 0 ? `+${d}` : d < 0 ? `${d}` : "–"))
    );
  }

  // Best response agent picker
  const seg = $("#g-br-agent");
  seg.replaceChildren(
    ...AGENTS.map((a) =>
      el("button", {
        class: a === game.brAgent ? "active" : "",
        onclick: () => { game.brAgent = a; $("#g-br-out").textContent = ""; gameRender(); },
      }, `Agent ${a}`)
    )
  );

  // Theorems
  const t = game.thm;
  const viol = (list) =>
    list.length
      ? list.map(([a, x, y]) => `${a}: ${greek(x)} ↪ ${greek(y)}`).join(", ")
      : "no agent holds an odd path between its own arguments";
  const verdict = (ok, yes, no) => el("span", { class: "tag " + (ok ? "in" : "out") }, ok ? yes : no);
  const sp = el("div", { class: "verdict" },
    el("div", {},
      el("div", { class: "t" }, "Strategyproof"),
      el("div", { class: "s" }, "Theorem 5.3, exact check over every report")),
    verdict(t.strategyproof, "yes", "no"));
  const rows = [sp];
  if (t.manipulation) {
    rows.push(el("div", { style: "padding:0 0 10px" },
      el("button", { class: "btn small", onclick: gameShowManipulation }, "Show a manipulation")));
  }
  rows.push(
    el("div", { class: "verdict" },
      el("div", {},
        el("div", { class: "t" }, "Theorem 5.4 condition, walks"),
        el("div", { class: "s" }, viol(t.violations_walk))),
      verdict(!t.violations_walk.length, "holds", "fails")),
    el("div", { class: "verdict" },
      el("div", {},
        el("div", { class: "t" }, "Theorem 5.4 condition, simple paths"),
        el("div", { class: "s" }, viol(t.violations_simple))),
      verdict(!t.violations_simple.length, "holds", "fails"))
  );
  $("#g-theorems").replaceChildren(...rows);

  $("#g-note").innerHTML = game.note || "";
  $("#g-note-group").hidden = !game.note;
}

function gameToggle(agent, arg) {
  const r = game.reports[agent];
  game.reports[agent] = r.includes(arg) ? r.filter((x) => x !== arg) : [...r, arg].sort(natural);
  $("#g-br-out").textContent = "";
  gameRender();
}

function gameBestResponse() {
  const a = game.brAgent;
  if (!game.types[a].length) {
    $("#g-br-out").textContent = `Agent ${a} has no arguments.`;
    return;
  }
  const br = call("best_response", { attacks: game.attacks, types: game.types, reports: game.reports, agent: a });
  const current = call("game_state", { attacks: game.attacks, types: game.types, reports: game.reports }).utilities[a].now;
  const best = br.reports[0];
  const hidden = game.types[a].filter((x) => !best.includes(x));
  const out = $("#g-br-out");
  out.replaceChildren();
  if (br.utility === current && best.join() === [...game.reports[a]].sort(natural).join()) {
    out.append(`Agent ${a} is already playing a best response (utility ${current}).`);
    return;
  }
  out.append(
    `Agent ${a}'s best move against the others: `,
    hidden.length ? `hide ${fmt(hidden)}` : "reveal everything",
    ` for utility ${br.utility}` + (br.utility > current ? ` (now ${current}). ` : ". "),
    el("a", { href: "#", onclick: (e) => { e.preventDefault(); game.reports[a] = best; gameRender(); out.textContent = ""; } }, "Play it")
  );
}

function gameShowManipulation() {
  const m = game.thm.manipulation;
  game.reports = { ...structuredClone(m.others), [m.agent]: m.report };
  for (const a of AGENTS) game.reports[a] ??= [];
  game.brAgent = m.agent;
  gameRender();
  $("#g-br-out").textContent = `Agent ${m.agent} hides ${fmt(m.hidden)}: utility ${m.truthful_utility} → ${m.manipulated_utility}.`;
}

function initGame() {
  game.cy = makeGraph($("#g-graph"));
  game.cy.on("tap", "node", (e) => {
    const id = e.target.id();
    const a = AGENTS.find((x) => game.types[x].includes(id));
    if (a) gameToggle(a, id);
  });
  game.cy.on("mouseover", "node", () => ($("#g-graph").style.cursor = "pointer"));
  game.cy.on("mouseout", "node", () => ($("#g-graph").style.cursor = ""));

  $("#g-preset").addEventListener("change", (e) => {
    const v = e.target.value;
    if (v === "random") gameRoll();
    else if (game.saved[v]) gameLoad(v, game.saved[v]);
    else gameLoad(v);
  });
  $("#g-p").addEventListener("input", (e) => ($("#g-p-val").textContent = Number(e.target.value).toFixed(2)));
  $("#g-p").addEventListener("change", gameRoll);
  $("#g-roll").addEventListener("click", gameRoll);
  $("#g-truth").addEventListener("click", () => {
    game.reports = structuredClone(game.types);
    $("#g-br-out").textContent = "";
    gameRender();
  });
  $("#g-br").addEventListener("click", gameBestResponse);
}

/* ============================================================
   Results
   ============================================================ */

const results = { summary: [], exhaustive: {}, q3: {} };

function parseCSV(text) {
  const [head, ...lines] = text.trim().split(/\r?\n/);
  const keys = head.split(",");
  return lines.map((l) => Object.fromEntries(l.split(",").map((v, i) => [keys[i], Number(v)])));
}

async function loadResults() {
  const get = (p) => fetch("../results/" + p).then((r) => (r.ok ? r.text() : Promise.reject(p)));
  try {
    results.summary = parseCSV(await get("summary.csv"));
    results.exhaustive.exhaustive = parseCSV(await get("exhaustive/summary.csv"));
    results.exhaustive["exhaustive-self-attacks"] = parseCSV(await get("exhaustive-self-attacks/summary.csv"));
    results.q3 = JSON.parse(await get("q3_examples.json"));
  } catch (err) {
    console.error("could not load results", err);
    return;
  }
  renderStats();
  renderChart();
  renderTable();
  renderExhaustive("exhaustive");
  renderQ3();
  renderLive({ done: 0, sp: 0, cond: 0, q2: 0, q3: 0 }, savedRow(Number($("#r-p").value)));
}

const savedRow = (p) => results.summary.find((r) => Math.abs(r.p - p) < 1e-9);

function renderStats() {
  const s = results.summary;
  const instances = s.reduce((t, r) => t + r.instances, 0);
  const sp = s.reduce((t, r) => t + r.strategyproof, 0);
  const q3 = s.reduce((t, r) => t + r.q3_walk, 0);
  const ex = Object.values(results.exhaustive).flat();
  const pairs = ex.reduce((t, r) => t + r.pairs, 0);
  const q2 =
    s.reduce((t, r) => t + r.q2_walk + r.q2_simple, 0) +
    ex.reduce((t, r) => t + r.q2_walk + r.q2_simple, 0);
  const stat = (n, d) => el("div", { class: "stat" }, el("div", { class: "n" }, n), el("div", { class: "d" }, d));
  $("#r-stats").replaceChildren(
    stat(num(instances), "random instances, checked exactly"),
    stat(num(pairs), "graph and argument-set pairs, n ≤ 5"),
    stat(String(q2), "counterexamples to Theorem 5.4"),
    stat(pct(q3 / sp, 0), "of strategyproof instances fail the condition")
  );
}

function renderChart() {
  const rows = results.summary;
  const W = 960, H = 340, m = { l: 48, r: 16, t: 16, b: 36 };
  const ps = rows.map((r) => r.p);
  const x = (p) => m.l + ((p - ps[0]) / (ps[ps.length - 1] - ps[0])) * (W - m.l - m.r);
  const y = (v) => m.t + (1 - v) * (H - m.t - m.b);
  const sp = rows.map((r) => [x(r.p), y(r.strategyproof / r.instances)]);
  const cd = rows.map((r) => [x(r.p), y(r.thm54_walk / r.instances)]);
  const path = (pts) => pts.map(([a, b], i) => `${i ? "L" : "M"}${a.toFixed(1)},${b.toFixed(1)}`).join("");
  const area = path(sp) + [...cd].reverse().map(([a, b]) => `L${a.toFixed(1)},${b.toFixed(1)}`).join("") + "Z";

  let grid = "", axis = "";
  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    grid += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}"/>`;
    axis += `<text x="${m.l - 10}" y="${y(v) + 4}" text-anchor="end">${v * 100}%</text>`;
  }
  for (const p of ps) axis += `<text x="${x(p)}" y="${H - 12}" text-anchor="middle">${p}</text>`;
  const dots = (pts, color, fill) =>
    pts.map(([a, b]) => `<circle cx="${a}" cy="${b}" r="3.5" fill="${fill}" stroke="${color}" stroke-width="1.5"/>`).join("");
  const step = (x(ps[1]) - x(ps[0])) / 2;
  const hits = rows
    .map((r, i) => `<rect data-i="${i}" x="${x(r.p) - step}" y="${m.t}" width="${step * 2}" height="${H - m.t - m.b}" fill="transparent"/>`)
    .join("");

  const wrap = $("#r-chart");
  wrap.innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Strategyproofness and Theorem 5.4 condition by attack probability">
      <g class="grid">${grid}</g>
      <g class="axis">${axis}<text x="${W - m.r}" y="${H - 12}" text-anchor="end" style="fill:var(--muted)"></text></g>
      <path d="${area}" fill="rgb(126 166 216 / 0.12)"/>
      <line id="r-cursor" y1="${m.t}" y2="${H - m.b}" stroke="#30333a" opacity="0"/>
      <path d="${path(cd)}" fill="none" stroke="#7ea6d8" stroke-width="1.75" stroke-dasharray="5 4"/>
      <path d="${path(sp)}" fill="none" stroke="#e7e8ea" stroke-width="2"/>
      ${dots(cd, "#7ea6d8", "#0c0d0f")}
      ${dots(sp, "#e7e8ea", "#0c0d0f")}
      <g id="r-hits">${hits}</g>
    </svg>
    <div class="tip" id="r-tip"></div>`;

  const tip = $("#r-tip"), cursor = $("#r-cursor");
  $$("#r-hits rect").forEach((rect) => {
    rect.addEventListener("mouseenter", () => {
      const r = rows[rect.dataset.i];
      tip.innerHTML =
        `<div class="mono" style="margin-bottom:4px">p = ${r.p}</div>` +
        `<div>Strategyproof <span class="mono">${pct(r.strategyproof / r.instances)}</span></div>` +
        `<div style="color:#7ea6d8">Condition holds <span class="mono">${pct(r.thm54_walk / r.instances)}</span></div>` +
        `<div class="muted">Q3 gap <span class="mono">${r.q3_walk}</span> instances</div>`;
      const left = (x(r.p) / W) * 100;
      tip.style.left = left > 70 ? "" : `calc(${left}% + 12px)`;
      tip.style.right = left > 70 ? `calc(${100 - left}% + 12px)` : "";
      tip.style.top = "12px";
      tip.style.opacity = 1;
      cursor.setAttribute("x1", x(r.p));
      cursor.setAttribute("x2", x(r.p));
      cursor.setAttribute("opacity", 1);
    });
    rect.addEventListener("mouseleave", () => {
      tip.style.opacity = 0;
      cursor.setAttribute("opacity", 0);
    });
  });
}

function renderTable() {
  const head = ["p", "Strategyproof", "Condition holds", "Q2", "Q3", "Costly rescue", "Never rescues", "Self-cycles"];
  const t = $("#r-table");
  t.replaceChildren(
    el("thead", {}, el("tr", {}, head.map((h) => el("th", {}, h)))),
    el("tbody", {},
      results.summary.map((r) =>
        el("tr", {},
          el("td", {}, r.p.toFixed(2)),
          el("td", {}, pct(r.strategyproof / r.instances)),
          el("td", {}, pct(r.thm54_walk / r.instances)),
          el("td", { class: r.q2_walk === 0 ? "zero" : "" }, r.q2_walk),
          el("td", {}, r.q3_walk),
          el("td", {}, r.q3_rescue_costs_as_much),
          el("td", {}, r.q3_never_rescues),
          el("td", {}, r.q3_self_cycles_only)))
    )
  );
}

function renderExhaustive(key) {
  const rows = results.exhaustive[key];
  const byN = new Map();
  for (const r of rows) {
    const acc = byN.get(r.n) || { n: r.n, pairs: 0, strategyproof: 0, cond_walk: 0, cond_simple: 0, q2: 0, q3: 0 };
    acc.pairs += r.pairs;
    acc.strategyproof += r.strategyproof;
    acc.cond_walk += r.cond_walk;
    acc.cond_simple += r.cond_simple;
    acc.q2 += r.q2_walk + r.q2_simple;
    acc.q3 += r.q3_walk;
    byN.set(r.n, acc);
  }
  const agg = [...byN.values()];
  const total = agg.reduce(
    (t, r) => {
      for (const k of Object.keys(t)) if (k !== "n") t[k] += r[k];
      return t;
    },
    { n: "Total", pairs: 0, strategyproof: 0, cond_walk: 0, cond_simple: 0, q2: 0, q3: 0 }
  );
  const head = ["Arguments", "Cases checked", "Strategyproof", "Condition (walks)", "Condition (simple)", "Q2", "Q3"];
  const row = (r, bold) =>
    el("tr", { style: bold ? "font-weight:500" : "" },
      el("td", {}, r.n),
      el("td", {}, num(r.pairs)),
      el("td", {}, num(r.strategyproof)),
      el("td", {}, num(r.cond_walk)),
      el("td", {}, num(r.cond_simple)),
      el("td", { class: r.q2 === 0 ? "zero" : "" }, num(r.q2)),
      el("td", {}, num(r.q3)));
  $("#r-ex-table").replaceChildren(
    el("thead", {}, el("tr", {}, head.map((h) => el("th", {}, h)))),
    el("tbody", {}, agg.map((r) => row(r)), row(total, true))
  );
}

function renderQ3() {
  const box = $("#r-q3");
  box.replaceChildren();
  const group = $("#g-saved");
  group.replaceChildren();
  for (const [reason, text] of Object.entries(Q3_TEXT)) {
    const examples = results.q3[reason] || [];
    examples.slice(0, 2).forEach((inst, i) => {
      const key = `saved-${reason}-${i}`;
      game.saved[key] = inst;
      group.append(el("option", { value: key }, `${text.title} · instance ${inst.id}`));
    });
    const totals = results.summary.reduce((t, r) => t + r[`q3_${reason}`], 0);
    box.append(
      el("div", { class: "card stack" },
        el("div", { class: "row", style: "justify-content:space-between" },
          el("h3", {}, text.title),
          el("span", { class: "mono muted" }, num(totals))),
        el("p", { class: "muted", style: "margin:0;font-size:13px;flex:1" }, text.body),
        examples.length
          ? el("button", { class: "btn small", style: "align-self:flex-start", onclick: () => go("game", `saved-${reason}-0`) }, "Open an example in the game →")
          : null)
    );
  }
}

async function liveRun() {
  const btn = $("#r-run");
  if (btn.dataset.running) {
    delete btn.dataset.running;
    return;
  }
  const p = Number($("#r-p").value);
  const n = Number($("#r-n").value);
  btn.dataset.running = "1";
  btn.textContent = "Stop";
  const base = Math.floor(Math.random() * 1e9);
  const c = { done: 0, sp: 0, cond: 0, q2: 0, q3: 0 };
  const saved = savedRow(p);
  for (let i = 0; i < n && btn.dataset.running; i++) {
    const r = call("sample", { p, seed: base + i });
    c.done++;
    c.sp += r.strategyproof;
    c.cond += r.thm54_walk;
    c.q2 += r.thm54_walk && !r.strategyproof;
    c.q3 += r.strategyproof && !r.thm54_walk;
    if (i % 4 === 0 || i === n - 1) {
      $("#r-progress").style.width = `${(100 * c.done) / n}%`;
      renderLive(c, saved);
      await tick();
    }
  }
  renderLive(c, saved);
  delete btn.dataset.running;
  btn.textContent = "Run again";
}

function renderLive(c, saved) {
  const live = (k) => (c.done ? pct(c[k] / c.done) : "–");
  const ref = (k) => (saved ? pct(saved[k] / saved.instances) : "–");
  const cells = [
    el("span", { class: "h" }, ""),
    el("span", { class: "h v" }, `This run · ${c.done}`),
    el("span", { class: "h v" }, saved ? "Saved · 1,000" : "Saved · n/a for this p"),
    el("span", {}, "Strategyproof"), el("span", { class: "v" }, live("sp")), el("span", { class: "v muted" }, ref("strategyproof")),
    el("span", {}, "Condition holds"), el("span", { class: "v" }, live("cond")), el("span", { class: "v muted" }, ref("thm54_walk")),
    el("span", {}, "Q3: strategyproof anyway"), el("span", { class: "v" }, live("q3")), el("span", { class: "v muted" }, ref("q3_walk")),
    el("span", {}, "Q2: counterexamples"), el("span", { class: "v" + (c.q2 ? " no" : " yes") }, String(c.q2)), el("span", { class: "v muted" }, saved ? String(saved.q2_walk) : "–"),
  ];
  $("#r-live").replaceChildren(...cells);
}

function initResults() {
  const bind = (id, out, f) =>
    $(id).addEventListener("input", (e) => ($(out).textContent = f(Number(e.target.value))));
  bind("#r-p", "#r-p-val", (v) => v.toFixed(2));
  bind("#r-n", "#r-n-val", (v) => v);
  $("#r-p").addEventListener("input", (e) => {
    if (!$("#r-run").dataset.running) {
      renderLive({ done: 0, sp: 0, cond: 0, q2: 0, q3: 0 }, savedRow(Number(e.target.value)));
    }
  });
  $("#r-run").addEventListener("click", liveRun);
  $$("#r-ex-mode button").forEach((b) =>
    b.addEventListener("click", () => {
      $$("#r-ex-mode button").forEach((x) => x.classList.toggle("active", x === b));
      renderExhaustive(b.dataset.m);
    })
  );
}

/* ============================================================
   Navigation
   ============================================================ */

let currentView = "playground";

function show(view) {
  currentView = view;
  $$("nav button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  $("#loading").style.display = view === "playground" || view === "game" ? "" : "none";
  const cy = view === "playground" ? pg.cy : view === "game" ? game.cy : null;
  if (cy) {
    cy.resize();
    fitGraph(cy);
  }
  if (history.replaceState) history.replaceState(null, "", `#${view}`);
  window.scrollTo(0, 0);
}

function go(view, preset) {
  show(view);
  if (!preset) return;
  if (view === "playground") pgLoad(preset);
  else if (view === "game") gameLoad(preset, game.saved[preset]);
}

function initNav() {
  $$("nav button").forEach((b) => b.addEventListener("click", () => show(b.dataset.view)));
  $$("[data-go]").forEach((b) =>
    b.addEventListener("click", () => {
      const [view, preset] = b.dataset.go.split(":");
      go(view, preset);
    })
  );
  let t;
  window.addEventListener("resize", () => {
    clearTimeout(t);
    t = setTimeout(() => {
      for (const cy of [pg.cy, game.cy]) if (cy && cy.width()) fitGraph(cy);
    }, 150);
  });
}

/* ============================================================
   Boot
   ============================================================ */

(async function main() {
  initNav();
  initPlayground();
  initGame();
  initResults();
  const hash = location.hash.slice(1);
  show(["playground", "game", "results", "how"].includes(hash) ? hash : "playground");
  pgLoad("fig51");
  gameLoad("ex510");
  loadResults();
  if (await bootPython()) {
    pgUpdate();
    gameLoad(game.key, game.saved[game.key]);
    $("#r-run").disabled = false;
  }
})();
