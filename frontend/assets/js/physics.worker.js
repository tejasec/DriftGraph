/**
 * physics.worker.js
 * High-Performance Obsidian-Style 2D Physics Simulation Worker for DriftGraph.
 *
 * Implements:
 * - Barnes-Hut Quadtree O(n log n) Many-Body Coulomb Repulsion (theta = 0.8)
 * - Spatial-Hash Broadphase Elastic Collisions with Restitution Impulse (e = 0.55)
 * - Degree-Scaled Hooke's Law Spring Edge Attraction
 * - Origin Centering Gravity & Velocity Damping
 * - Kinematic Pinning during Drag & Momentum Fling
 * - Radial Boundary Elastic Guard
 * - Alpha-Decay & Minimal Kinetic Energy Sleep State
 */

"use strict";

/* ============================================================
   1. BARNES-HUT QUADTREE (O(n log n) N-Body Repulsion)
   ============================================================ */
class BHNode {
  constructor(x, y, size) {
    this.x = x; // Center x
    this.y = y; // Center y
    this.size = size; // Half-width or full width
    this.mass = 0;
    this.cx = 0; // Center of mass x
    this.cy = 0; // Center of mass y
    this.bodyIndex = -1; // Index if leaf with 1 body, else -1
    this.children = null; // [nw, ne, sw, se]
  }

  insert(bodyIdx, bx, by, bm) {
    if (this.mass === 0) {
      this.bodyIndex = bodyIdx;
      this.mass = bm;
      this.cx = bx;
      this.cy = by;
      return;
    }

    if (!this.children) {
      this.subdivide();
      const oldIdx = this.bodyIndex;
      this.bodyIndex = -1;
      this.insertChild(oldIdx, this.cx, this.cy, this.mass);
    }

    this.insertChild(bodyIdx, bx, by, bm);

    const totalMass = this.mass + bm;
    this.cx = (this.cx * this.mass + bx * bm) / totalMass;
    this.cy = (this.cy * this.mass + by * bm) / totalMass;
    this.mass = totalMass;
  }

  subdivide() {
    const half = this.size / 2;
    const quarter = half / 2;
    this.children = [
      new BHNode(this.x - quarter, this.y - quarter, half), // NW
      new BHNode(this.x + quarter, this.y - quarter, half), // NE
      new BHNode(this.x - quarter, this.y + quarter, half), // SW
      new BHNode(this.x + quarter, this.y + quarter, half)  // SE
    ];
  }

  insertChild(bodyIdx, bx, by, bm) {
    const isEast = bx >= this.x;
    const isSouth = by >= this.y;
    const childIdx = (isSouth ? 2 : 0) + (isEast ? 1 : 0);
    this.children[childIdx].insert(bodyIdx, bx, by, bm);
  }

  computeRepulsion(px, py, bodyIdx, theta, kRepel, forces) {
    if (this.mass === 0) return;

    const dx = px - this.cx;
    const dy = py - this.cy;
    const distSq = dx * dx + dy * dy;

    if (this.children) {
      const dist = Math.sqrt(distSq) || 0.001;
      if (this.size / dist < theta) {
        // Far enough away: treat quadrant as single center of mass
        const force = (kRepel * this.mass) / (distSq + 30.0);
        forces.fx += (dx / dist) * force;
        forces.fy += (dy / dist) * force;
      } else {
        // Recurse into children
        for (let i = 0; i < 4; i++) {
          this.children[i].computeRepulsion(px, py, bodyIdx, theta, kRepel, forces);
        }
      }
    } else if (this.bodyIndex >= 0 && this.bodyIndex !== bodyIdx) {
      const dist = Math.sqrt(distSq) || 0.001;
      const force = (kRepel * this.mass) / (distSq + 30.0);
      forces.fx += (dx / dist) * force;
      forces.fy += (dy / dist) * force;
    }
  }
}

/* ============================================================
   2. PHYSICS SIMULATION ENGINE
   ============================================================ */
class PhysicsEngine {
  constructor(options = {}) {
    this.options = Object.assign(
      {
        kRepel: 5200,
        theta: 0.8,
        kSpring: 0.045,
        springRestBase: 85,
        kCenter: 0.0022,
        damping: 0.85, // 1 - mu (mu = 0.15)
        restitution: 0.55,
        collisionPadding: 4,
        maxVelocity: 28,
        alphaDecay: 0.976,
        sleepThreshold: 0.0015,
        boundaryRadius: 1300
      },
      options
    );

    this.nodeCount = 0;
    this.edgeCount = 0;

    // Node Arrays
    this.nodeIds = [];
    this.idToIndex = new Map();
    this.posX = new Float32Array(0);
    this.posY = new Float32Array(0);
    this.velX = new Float32Array(0);
    this.velY = new Float32Array(0);
    this.forcesX = new Float32Array(0);
    this.forcesY = new Float32Array(0);
    this.mass = new Float32Array(0);
    this.radius = new Float32Array(0);
    this.collisionRadius = new Float32Array(0);
    this.pinned = new Uint8Array(0);
    this.baseX = new Float32Array(0);
    this.baseY = new Float32Array(0);

    // Edge Arrays
    this.edgeSrc = new Int32Array(0);
    this.edgeTgt = new Int32Array(0);
    this.edgeRest = new Float32Array(0);
    this.edgeWeight = new Float32Array(0);

    // Spatial Hash Grid for O(n) Collision Detection
    this.gridCellSize = 40;
    this.spatialGrid = new Map();

    // Simulation lifecycle
    this.alpha = 1.0;
    this.isRunning = false;
    this.iteration = 0;
  }

  init(nodes, edges, options = {}) {
    this.options = Object.assign(this.options, options);
    this.nodeCount = nodes.length;
    this.nodeIds = new Array(this.nodeCount);
    this.idToIndex.clear();

    this.posX = new Float32Array(this.nodeCount);
    this.posY = new Float32Array(this.nodeCount);
    this.velX = new Float32Array(this.nodeCount);
    this.velY = new Float32Array(this.nodeCount);
    this.forcesX = new Float32Array(this.nodeCount);
    this.forcesY = new Float32Array(this.nodeCount);
    this.mass = new Float32Array(this.nodeCount);
    this.radius = new Float32Array(this.nodeCount);
    this.collisionRadius = new Float32Array(this.nodeCount);
    this.pinned = new Uint8Array(this.nodeCount);
    this.baseX = new Float32Array(this.nodeCount);
    this.baseY = new Float32Array(this.nodeCount);

    const degMap = new Map();

    for (let i = 0; i < this.nodeCount; i++) {
      const n = nodes[i];
      const id = n.data ? n.data.id : (n.id || String(i));
      this.nodeIds[i] = id;
      this.idToIndex.set(id, i);

      const px = typeof n.x === "number" ? n.x : (n.position && typeof n.position.x === "number" ? n.position.x : (Math.random() - 0.5) * 600);
      const py = typeof n.y === "number" ? n.y : (n.position && typeof n.position.y === "number" ? n.position.y : (Math.random() - 0.5) * 600);

      this.posX[i] = px;
      this.posY[i] = py;
      this.baseX[i] = px;
      this.baseY[i] = py;
      this.velX[i] = typeof n.vx === "number" ? n.vx : 0;
      this.velY[i] = typeof n.vy === "number" ? n.vy : 0;

      const deg = typeof n.degree === "number" ? n.degree : (n.data && typeof n.data.degree === "number" ? n.data.degree : 1);
      degMap.set(id, deg);

      const r = typeof n.radius === "number" ? n.radius : (3.0 + Math.min(6.0, Math.log(deg + 1)));
      this.radius[i] = r;
      this.collisionRadius[i] = r + this.options.collisionPadding;
      this.mass[i] = Math.max(1.0, Math.sqrt(deg + 1));
      this.pinned[i] = n.pinned ? 1 : 0;
    }

    // Filter and prepare edges
    const validEdges = [];
    if (edges && edges.length > 0) {
      for (let j = 0; j < edges.length; j++) {
        const e = edges[j];
        const s = e.data ? e.data.source : (e.source !== undefined ? e.source : null);
        const t = e.data ? e.data.target : (e.target !== undefined ? e.target : null);
        if (s !== null && t !== null && this.idToIndex.has(s) && this.idToIndex.has(t)) {
          const u = this.idToIndex.get(s);
          const v = this.idToIndex.get(t);
          if (u !== v) {
            const weight = (e.data && typeof e.data.weight === "number") ? e.data.weight : (typeof e.weight === "number" ? e.weight : 1.0);
            const degU = degMap.get(s) || 1;
            const degV = degMap.get(t) || 1;
            // Resting length scales inversely with hub degree so dense clusters pull together
            const rest = this.options.springRestBase / Math.sqrt(Math.min(degU, degV) + 1);
            validEdges.push({ u, v, weight, rest });
          }
        }
      }
    }

    this.edgeCount = validEdges.length;
    this.edgeSrc = new Int32Array(this.edgeCount);
    this.edgeTgt = new Int32Array(this.edgeCount);
    this.edgeRest = new Float32Array(this.edgeCount);
    this.edgeWeight = new Float32Array(this.edgeCount);

    for (let k = 0; k < this.edgeCount; k++) {
      this.edgeSrc[k] = validEdges[k].u;
      this.edgeTgt[k] = validEdges[k].v;
      this.edgeRest[k] = validEdges[k].rest;
      this.edgeWeight[k] = validEdges[k].weight;
    }

    // Compute maximum collision diameter for spatial grid
    let maxR = 10;
    for (let i = 0; i < this.nodeCount; i++) {
      if (this.collisionRadius[i] > maxR) maxR = this.collisionRadius[i];
    }
    this.gridCellSize = Math.max(30, Math.ceil(maxR * 2));

    this.alpha = 1.0;
    this.iteration = 0;
    this.isRunning = options.autoStart !== false;
  }

  wake(alpha = 0.35) {
    this.alpha = Math.max(this.alpha, alpha);
    this.isRunning = true;
  }

  setNodePosition(id, x, y, pin = false, wakeAlpha = 0) {
    const idx = this.idToIndex.get(id);
    if (idx !== undefined) {
      this.posX[idx] = x;
      this.posY[idx] = y;
      this.baseX[idx] = x;
      this.baseY[idx] = y;
      this.velX[idx] = 0;
      this.velY[idx] = 0;
      if (pin) this.pinned[idx] = 1;
      if (wakeAlpha > 0) {
        this.wake(wakeAlpha);
      }
    }
  }

  resolveKinematicCollision(draggedId) {
    const N = this.nodeCount;
    if (N < 2) return;

    const dragIdx = this.idToIndex.get(draggedId);
    if (dragIdx === undefined) return;

    const padding = this.options.collisionPadding !== undefined ? this.options.collisionPadding : 4.0;
    const restitution = this.options.restitution !== undefined ? this.options.restitution : 0.55;

    // Hard elastic body collision deflection: Rc = r_node + 4px
    for (let iter = 0; iter < 2; iter++) {
      for (let j = 0; j < N; j++) {
        if (j === dragIdx) continue;
        const dx = this.posX[j] - this.posX[dragIdx];
        const dy = this.posY[j] - this.posY[dragIdx];
        const rSum = this.radius[dragIdx] + this.radius[j] + padding;
        const distSq = dx * dx + dy * dy;

        if (distSq < rSum * rSum) {
          const dist = Math.sqrt(distSq) || 0.001;
          const overlap = rSum - dist;
          const nx = dx / dist;
          const ny = dy / dist;

          // Displace the unpinned surrounding node out of collision zone
          this.posX[j] += nx * overlap;
          this.posY[j] += ny * overlap;
          this.baseX[j] = this.posX[j];
          this.baseY[j] = this.posY[j];

          // Elastic deflection impulse
          this.velX[j] = nx * (1 + restitution) * 2.0;
          this.velY[j] = ny * (1 + restitution) * 2.0;
        }
      }
    }
  }

  unpinNode(id, vx = 0, vy = 0) {
    const idx = this.idToIndex.get(id);
    if (idx !== undefined) {
      this.pinned[idx] = 0;
      this.baseX[idx] = this.posX[idx];
      this.baseY[idx] = this.posY[idx];
      this.velX[idx] = vx;
      this.velY[idx] = vy;
      if (Math.hypot(vx, vy) > 1.5) {
        this.wake(0.12);
      }
    }
  }

  applyAmbientRepulsion(mx, my, radius = 125, kMouse = 28000, alphaTarget = 0.08) {
    const N = this.nodeCount;
    if (N === 0) return;
    const r2 = radius * radius;
    const eps = 12.0;

    for (let i = 0; i < N; i++) {
      if (this.pinned[i]) continue;
      const dx = this.posX[i] - mx;
      const dy = this.posY[i] - my;
      const d2 = dx * dx + dy * dy;
      if (d2 < r2 && d2 > 0.01) {
        const d = Math.sqrt(d2);
        const ux = dx / d;
        const uy = dy / d;
        const f = kMouse / ((d + eps) * (d + eps));
        const m = this.mass[i] || 1.0;
        this.velX[i] += (ux * f) / m;
        this.velY[i] += (uy * f) / m;
      }
    }
    this.wake(alphaTarget);
  }

  step() {
    const N = this.nodeCount;
    if (N === 0) return { totalEnergy: 0, alpha: 0, sleeping: true };

    const {
      kRepel,
      theta,
      kSpring,
      kCenter,
      damping,
      restitution,
      maxVelocity,
      alphaDecay,
      sleepThreshold,
      boundaryRadius
    } = this.options;

    // Reset forces
    this.forcesX.fill(0);
    this.forcesY.fill(0);

    // 1. Build Barnes-Hut Quadtree
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (let i = 0; i < N; i++) {
      const px = this.posX[i];
      const py = this.posY[i];
      if (px < minX) minX = px;
      if (px > maxX) maxX = px;
      if (py < minY) minY = py;
      if (py > maxY) maxY = py;
    }

    const margin = 40;
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const treeSize = Math.max(maxX - minX, maxY - minY) + margin * 2;
    const bhRoot = new BHNode(cx, cy, Math.max(treeSize, 200));

    for (let i = 0; i < N; i++) {
      bhRoot.insert(i, this.posX[i], this.posY[i], this.mass[i]);
    }

    // 2. Many-Body Coulomb Repulsion via Barnes-Hut (O(n log n))
    const forces = { fx: 0, fy: 0 };
    for (let i = 0; i < N; i++) {
      forces.fx = 0;
      forces.fy = 0;
      bhRoot.computeRepulsion(this.posX[i], this.posY[i], i, theta, kRepel, forces);
      this.forcesX[i] += forces.fx;
      this.forcesY[i] += forces.fy;
    }

    // 3. Spring Edge Attraction (Hooke's Law)
    const E = this.edgeCount;
    for (let k = 0; k < E; k++) {
      const u = this.edgeSrc[k];
      const v = this.edgeTgt[k];

      const dx = this.posX[v] - this.posX[u];
      const dy = this.posY[v] - this.posY[u];
      const dist = Math.hypot(dx, dy) || 0.001;
      const displacement = dist - this.edgeRest[k];
      const springF = displacement * kSpring * this.edgeWeight[k];

      const sX = (dx / dist) * springF;
      const sY = (dy / dist) * springF;

      this.forcesX[u] += sX;
      this.forcesY[u] += sY;
      this.forcesX[v] -= sX;
      this.forcesY[v] -= sY;
    }

    // 4. Center Gravity & Boundary Guard & Semi-Implicit Euler Integration
    let totalKineticEnergy = 0;
    const alpha = this.alpha;

    for (let i = 0; i < N; i++) {
      if (this.pinned[i]) {
        this.velX[i] = 0;
        this.velY[i] = 0;
        continue;
      }

      // Weak center gravity pulling toward origin (0, 0)
      this.forcesX[i] -= this.posX[i] * kCenter * this.mass[i];
      this.forcesY[i] -= this.posY[i] * kCenter * this.mass[i];

      // Gentle baseline elastic restoring force toward baseline coordinates
      const kBase = 0.025;
      this.forcesX[i] -= (this.posX[i] - this.baseX[i]) * kBase * this.mass[i];
      this.forcesY[i] -= (this.posY[i] - this.baseY[i]) * kBase * this.mass[i];
      this.baseX[i] += (this.posX[i] - this.baseX[i]) * 0.008;
      this.baseY[i] += (this.posY[i] - this.baseY[i]) * 0.008;

      // Invisible radial elastic boundary guard
      const rDist = Math.hypot(this.posX[i], this.posY[i]);
      if (rDist > boundaryRadius) {
        const excess = rDist - boundaryRadius;
        const bF = excess * 0.06;
        this.forcesX[i] -= (this.posX[i] / rDist) * bF;
        this.forcesY[i] -= (this.posY[i] / rDist) * bF;
      }

      // Acceleration scaled by temperature (alpha)
      const ax = (this.forcesX[i] / this.mass[i]) * alpha;
      const ay = (this.forcesY[i] / this.mass[i]) * alpha;

      // Semi-implicit Euler integration with velocity damping (friction)
      this.velX[i] = (this.velX[i] + ax) * damping;
      this.velY[i] = (this.velY[i] + ay) * damping;

      // Speed clamp
      const spd = Math.hypot(this.velX[i], this.velY[i]);
      if (spd > maxVelocity) {
        const scale = maxVelocity / spd;
        this.velX[i] *= scale;
        this.velY[i] *= scale;
      }

      this.posX[i] += this.velX[i];
      this.posY[i] += this.velY[i];

      totalKineticEnergy += this.velX[i] * this.velX[i] + this.velY[i] * this.velY[i];
    }

    // 5. Elastic Collision Detection & Resolution via Spatial Hash
    this.resolveCollisions(restitution);

    // 6. Alpha decay
    this.alpha *= alphaDecay;
    this.iteration++;

    const isSleeping = this.alpha < sleepThreshold && totalKineticEnergy < 0.02;
    if (isSleeping) {
      this.isRunning = false;
    }

    return {
      totalEnergy: totalKineticEnergy,
      alpha: this.alpha,
      sleeping: isSleeping
    };
  }

  resolveCollisions(restitution) {
    const N = this.nodeCount;
    if (N < 2) return;

    const cellSize = this.gridCellSize;
    const grid = this.spatialGrid;
    grid.clear();

    // Populate spatial hash grid: key -> Array of indices
    for (let i = 0; i < N; i++) {
      const gx = Math.floor(this.posX[i] / cellSize);
      const gy = Math.floor(this.posY[i] / cellSize);
      const key = `${gx},${gy}`;
      let cell = grid.get(key);
      if (!cell) {
        cell = [];
        grid.set(key, cell);
      }
      cell.push(i);
    }

    // Resolve overlaps and apply bounce impulse
    for (let i = 0; i < N; i++) {
      const gx = Math.floor(this.posX[i] / cellSize);
      const gy = Math.floor(this.posY[i] / cellSize);
      const p1Pinned = this.pinned[i];
      const r1 = this.collisionRadius[i];
      const m1 = this.mass[i];

      // Check 9 neighboring grid cells
      for (let ox = -1; ox <= 1; ox++) {
        for (let oy = -1; oy <= 1; oy++) {
          const key = `${gx + ox},${gy + oy}`;
          const cell = grid.get(key);
          if (!cell) continue;

          for (let c = 0; c < cell.length; c++) {
            const j = cell[c];
            if (i >= j) continue; // Each pair processed once

            const dx = this.posX[j] - this.posX[i];
            const dy = this.posY[j] - this.posY[i];
            const rSum = r1 + this.collisionRadius[j];
            const distSq = dx * dx + dy * dy;

            if (distSq < rSum * rSum) {
              const dist = Math.sqrt(distSq) || 0.001;
              const overlap = rSum - dist;
              const nx = dx / dist;
              const ny = dy / dist;

              const p2Pinned = this.pinned[j];
              const m2 = this.mass[j];

              // Hard anti-overlap displacement
              if (!p1Pinned && !p2Pinned) {
                const disp = overlap * 0.5;
                this.posX[i] -= nx * disp;
                this.posY[i] -= ny * disp;
                this.posX[j] += nx * disp;
                this.posY[j] += ny * disp;
              } else if (!p1Pinned && p2Pinned) {
                this.posX[i] -= nx * overlap;
                this.posY[i] -= ny * overlap;
              } else if (p1Pinned && !p2Pinned) {
                this.posX[j] += nx * overlap;
                this.posY[j] += ny * overlap;
              }

              // Elastic restitution impulse
              const relVx = this.velX[i] - this.velX[j];
              const relVy = this.velY[i] - this.velY[j];
              const vDotN = relVx * nx + relVy * ny;

              if (vDotN > 0) {
                const invM1 = p1Pinned ? 0 : 1 / m1;
                const invM2 = p2Pinned ? 0 : 1 / m2;
                const invMassSum = invM1 + invM2;
                if (invMassSum > 0) {
                  const impulse = ((1 + restitution) * vDotN) / invMassSum;
                  if (!p1Pinned) {
                    this.velX[i] -= impulse * invM1 * nx;
                    this.velY[i] -= impulse * invM1 * ny;
                  }
                  if (!p2Pinned) {
                    this.velX[j] += impulse * invM2 * nx;
                    this.velY[j] += impulse * invM2 * ny;
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  getFlatPositions() {
    const N = this.nodeCount;
    const flat = new Float32Array(N * 2);
    for (let i = 0; i < N; i++) {
      flat[i * 2] = this.posX[i];
      flat[i * 2 + 1] = this.posY[i];
    }
    return flat;
  }
}

/* ============================================================
   3. WEB WORKER MESSAGE HANDLER
   ============================================================ */
let engine = null;
let loopTimer = null;
const TARGET_FRAME_MS = 16.67; // 60 FPS target

function physicsLoop() {
  if (!engine || !engine.isRunning) return;

  const result = engine.step();
  const positions = engine.getFlatPositions();

  if (typeof self !== "undefined" && typeof self.postMessage === "function") {
    if (result.sleeping) {
      self.postMessage({
        type: "sleep",
        positions: positions.buffer,
        iteration: engine.iteration,
        totalEnergy: result.totalEnergy
      }, [positions.buffer]);
    } else {
      self.postMessage({
        type: "tick",
        positions: positions.buffer,
        iteration: engine.iteration,
        totalEnergy: result.totalEnergy,
        alpha: result.alpha
      }, [positions.buffer]);

      loopTimer = setTimeout(physicsLoop, TARGET_FRAME_MS);
    }
  }
}

if (typeof self !== "undefined") {
  self.onmessage = function (e) {
    const msg = e.data || {};

    switch (msg.type) {
      case "init": {
        if (loopTimer) clearTimeout(loopTimer);
        engine = new PhysicsEngine(msg.options);
        engine.init(msg.nodes || [], msg.edges || [], msg.options || {});
        engine.wake(1.0);
        physicsLoop();
        break;
      }

      case "step": {
        if (engine) {
          const result = engine.step();
          const positions = engine.getFlatPositions();
          self.postMessage({
            type: "step_result",
            positions: positions.buffer,
            sleeping: result.sleeping
          }, [positions.buffer]);
        }
        break;
      }

      case "wake": {
        if (engine) {
          engine.wake(msg.alpha || 0.35);
          if (loopTimer) clearTimeout(loopTimer);
          physicsLoop();
        }
        break;
      }

      case "drag_start": {
        if (engine) {
          engine.setNodePosition(msg.id, msg.x, msg.y, true, 0);
          engine.resolveKinematicCollision(msg.id);
        }
        break;
      }

      case "drag_move": {
        if (engine) {
          engine.setNodePosition(msg.id, msg.x, msg.y, true, 0);
          engine.resolveKinematicCollision(msg.id);
          const positions = engine.getFlatPositions();
          self.postMessage({
            type: "tick",
            positions: positions.buffer,
            iteration: engine.iteration,
            totalEnergy: 0,
            alpha: 0
          }, [positions.buffer]);
        }
        break;
      }

      case "drag_end": {
        if (engine) {
          engine.unpinNode(msg.id, msg.vx || 0, msg.vy || 0);
          const spd = Math.hypot(msg.vx || 0, msg.vy || 0);
          if (spd > 1.5) {
            engine.wake(0.12);
            if (!engine.isRunning) {
              if (loopTimer) clearTimeout(loopTimer);
              physicsLoop();
            }
          }
        }
        break;
      }

      case "ambient_repel": {
        // Scoped Cursor Physics: Ambient repulsion is strictly disabled in explorer canvas
        // Only active if explicitly flagged for hero landing view
        if (engine && msg.isHeroActive) {
          engine.applyAmbientRepulsion(msg.x, msg.y, msg.radius, msg.kMouse, msg.alpha || 0.08);
          if (!engine.isRunning) {
            if (loopTimer) clearTimeout(loopTimer);
            physicsLoop();
          }
        }
        break;
      }

      case "update_options": {
        if (engine && msg.options) {
          Object.assign(engine.options, msg.options);
        }
        break;
      }

      case "stop": {
        if (engine) engine.isRunning = false;
        if (loopTimer) clearTimeout(loopTimer);
        break;
      }

      default:
        break;
    }
  };
}

// Export PhysicsEngine if required in CommonJS / testing
if (typeof module !== "undefined" && module.exports) {
  module.exports = { PhysicsEngine, BHNode };
}
