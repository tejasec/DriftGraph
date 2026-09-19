/**
 * graph-worker.js
 * Off-thread force-directed physics layout worker for DriftGraph.
 * Decouples physics calculations from the main UI thread to ensure
 * smooth 60 FPS pan, zoom, and interaction on large graphs.
 */

let nodes = new Map();
let edges = [];
let options = {
  repulsion: 4500,
  springLength: 90,
  springCoeff: 0.0008,
  damping: 0.85,
  centerPull: 0.001,
  maxVelocity: 30,
  stopEnergy: 0.05,
  maxIterations: 500
};

let isRunning = false;
let timerId = null;
let iteration = 0;

function initSimulation(nodeList, edgeList, opts = {}) {
  options = Object.assign({}, options, opts);
  nodes.clear();
  edges = [];
  iteration = 0;

  if (Array.isArray(nodeList)) {
    for (const n of nodeList) {
      const id = (n.data && n.data.id) ? n.data.id : (n.id || String(n));
      const pos = n.position || {};
      const x = typeof pos.x === "number" ? pos.x : (Math.random() - 0.5) * 800;
      const y = typeof pos.y === "number" ? pos.y : (Math.random() - 0.5) * 800;
      nodes.set(id, {
        id,
        x,
        y,
        vx: 0,
        vy: 0,
        pinned: Boolean(n.pinned || (n.data && n.data.pinned)),
        mass: (n.data && n.data.degree) ? Math.sqrt(n.data.degree) + 1 : 1
      });
    }
  }

  if (Array.isArray(edgeList)) {
    for (const e of edgeList) {
      const src = (e.data && e.data.source) ? e.data.source : e.source;
      const tgt = (e.data && e.data.target) ? e.data.target : e.target;
      if (src && tgt && nodes.has(src) && nodes.has(tgt)) {
        edges.push({
          source: src,
          target: tgt,
          weight: (e.data && e.data.weight) ? Math.min(e.data.weight, 5) : 1
        });
      }
    }
  }
}

function stepSimulation() {
  const nodeList = Array.from(nodes.values());
  const nCount = nodeList.length;
  if (nCount === 0) return { totalEnergy: 0, positions: {} };

  // 1. Reset forces
  const fx = new Float32Array(nCount);
  const fy = new Float32Array(nCount);
  const idToIndex = new Map();
  for (let i = 0; i < nCount; i++) {
    idToIndex.set(nodeList[i].id, i);
  }

  // 2. Node-node repulsion (Coulomb force)
  for (let i = 0; i < nCount; i++) {
    const na = nodeList[i];
    for (let j = i + 1; j < nCount; j++) {
      const nb = nodeList[j];
      let dx = nb.x - na.x;
      let dy = nb.y - na.y;
      let distSq = dx * dx + dy * dy;
      if (distSq < 1.0) {
        dx = (Math.random() - 0.5) * 2;
        dy = (Math.random() - 0.5) * 2;
        distSq = 1.0;
      }
      const dist = Math.sqrt(distSq);
      // Soft-clamped inverse square
      const force = (options.repulsion * na.mass * nb.mass) / distSq;
      const fX = (dx / dist) * force;
      const fY = (dy / dist) * force;

      fx[i] -= fX;
      fy[i] -= fY;
      fx[j] += fX;
      fy[j] += fY;
    }
  }

  // 3. Edge spring attraction (Hooke's law)
  for (let e = 0; e < edges.length; e++) {
    const edge = edges[e];
    const i = idToIndex.get(edge.source);
    const j = idToIndex.get(edge.target);
    if (i === undefined || j === undefined) continue;

    const na = nodeList[i];
    const nb = nodeList[j];
    const dx = nb.x - na.x;
    const dy = nb.y - na.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
    const displacement = dist - options.springLength;
    const force = displacement * options.springCoeff * edge.weight;
    const fX = (dx / dist) * force;
    const fY = (dy / dist) * force;

    fx[i] += fX;
    fy[i] += fY;
    fx[j] -= fX;
    fy[j] -= fY;
  }

  // 4. Center pull and integration
  let totalEnergy = 0;
  const positions = {};

  for (let i = 0; i < nCount; i++) {
    const node = nodeList[i];
    if (node.pinned) {
      node.vx = 0;
      node.vy = 0;
      positions[node.id] = { x: node.x, y: node.y };
      continue;
    }

    // Center gravity
    fx[i] -= node.x * options.centerPull * node.mass;
    fy[i] -= node.y * options.centerPull * node.mass;

    // Update velocity with damping
    node.vx = (node.vx + fx[i] / node.mass) * options.damping;
    node.vy = (node.vy + fy[i] / node.mass) * options.damping;

    // Clamp velocity
    const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
    if (speed > options.maxVelocity) {
      node.vx = (node.vx / speed) * options.maxVelocity;
      node.vy = (node.vy / speed) * options.maxVelocity;
    }

    // Update position
    node.x += node.vx;
    node.y += node.vy;

    const energy = node.vx * node.vx + node.vy * node.vy;
    totalEnergy += energy;
    positions[node.id] = { x: node.x, y: node.y };
  }

  return { totalEnergy, positions };
}

function runLoop() {
  if (!isRunning) return;

  const result = stepSimulation();
  iteration++;

  // Batch post positions to main thread
  self.postMessage({
    type: "tick",
    iteration,
    totalEnergy: result.totalEnergy,
    positions: result.positions
  });

  if (result.totalEnergy < options.stopEnergy || iteration >= options.maxIterations) {
    isRunning = false;
    self.postMessage({
      type: "end",
      iteration,
      positions: result.positions
    });
  } else {
    // Schedule next physics step (~25ms for smooth 40-60 updates/sec without thrashing)
    timerId = setTimeout(runLoop, 20);
  }
}

function start() {
  if (isRunning) return;
  isRunning = true;
  iteration = 0;
  runLoop();
}

function stop() {
  isRunning = false;
  if (timerId !== null) {
    clearTimeout(timerId);
    timerId = null;
  }
}

self.onmessage = function(e) {
  const msg = e.data || {};
  switch (msg.type) {
    case "init":
      stop();
      initSimulation(msg.nodes, msg.edges, msg.options);
      if (msg.autoStart !== false) {
        start();
      }
      break;

    case "start":
      start();
      break;

    case "step":
      const res = stepSimulation();
      self.postMessage({
        type: "tick",
        stepOnly: true,
        positions: res.positions
      });
      break;

    case "stop":
      stop();
      break;

    case "update_node": {
      const node = nodes.get(msg.id);
      if (node) {
        if (typeof msg.x === "number") node.x = msg.x;
        if (typeof msg.y === "number") node.y = msg.y;
        if (typeof msg.pinned === "boolean") node.pinned = msg.pinned;
        if (msg.pinned) {
          node.vx = 0;
          node.vy = 0;
        } else if (!isRunning) {
          // Wake up simulation briefly to relax connected neighbors
          options.maxIterations = Math.max(iteration + 50, options.maxIterations);
          start();
        }
      }
      break;
    }

    default:
      break;
  }
};
