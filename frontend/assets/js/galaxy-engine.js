/**
 * galaxy-engine.js
 * High-Performance Obsidian-Style Galaxy Graph Visualization Engine with
 * Real-Time 2D Physics Simulation, Node Collision Engine & Semantic Color-Coding.
 *
 * Features:
 * - Layered Dual-Canvas Architecture (Static bg-canvas + Interactive hover-canvas)
 * - Real-Time 2D Force-Directed Physics Engine (Worker-backed with direct fallback)
 * - Barnes-Hut Quadtree O(n log n) Coulomb Repulsion (theta = 0.8)
 * - Elastic Hard Collisions with Restitution Impulse (e = 0.55, padding = 4px, anti-overlap)
 * - Degree-Scaled Hooke's Law Spring Edges & Radial Boundary Guard
 * - Categorical Semantic Color-Coding (6-hue semantic palette + golden-ratio HSL distribution)
 * - Degree-Modulated Luminance Attenuation & Hub Perimeter Auras
 * - Pre-compiled Color String Cache for Zero-GC 60 FPS Canvas Redraws
 * - Kinematic Drag Pinning & Momentum Fling Mechanics
 * - 2D Quadtree Spatial Indexing for O(log n) Instantaneous Hit-Testing
 * - Starburst Spotlight Hover Effect with 1-Hop Subgraph Illumination & Monospaced Pill
 * - 60 FPS Viewport Pan/Zoom with Matrix Transforms & Zero DOM Overhead
 */

(function (root, factory) {
  if (typeof define === "function" && define.amd) {
    define([], factory);
  } else if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.ObsidianGalaxyEngine = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const GOLDEN_ANGLE_RAD = 137.507764 * (Math.PI / 180); // ~2.39996323 rad

  /* ============================================================
     1. SEMANTIC COLOR CODING & VISUAL HIERARCHY
     ============================================================ */
  const DEFAULT_SEMANTIC_PALETTE = [
    "#38bdf8", // 0: Electric Cyan
    "#34d399", // 1: Vibrant Emerald
    "#a855f7", // 2: Rich Purple
    "#fbbf24", // 3: Warm Amber
    "#f43f5e", // 4: Soft Coral
    "#94a3b8"  // Default / Unlinked: Slate Blue-Gray
  ];
  const NEUTRAL_LEAF_COLOR = "#94a3b8"; // Muted neutral gray for singletons

  function hexToRgb(hex) {
    let c = String(hex).replace("#", "");
    if (c.length === 3) c = c.split("").map(ch => ch + ch).join("");
    const num = parseInt(c, 16) || 0;
    return {
      r: (num >> 16) & 255,
      g: (num >> 8) & 255,
      b: num & 255
    };
  }

  function rgbToHex(r, g, b) {
    return "#" + [r, g, b].map(x => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, "0")).join("");
  }

  function rgbToHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;
    if (max === min) {
      h = s = 0;
    } else {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        case b: h = (r - g) / d + 4; break;
      }
      h /= 6;
    }
    return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) };
  }

  function hslToRgb(h, s, l) {
    h /= 360; s /= 100; l /= 100;
    let r, g, b;
    if (s === 0) {
      r = g = b = l;
    } else {
      const hue2rgb = (p, q, t) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1/6) return p + (q - p) * 6 * t;
        if (t < 1/2) return q;
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
        return p;
      };
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      r = hue2rgb(p, q, h + 1/3);
      g = hue2rgb(p, q, h);
      b = hue2rgb(p, q, h - 1/3);
    }
    return {
      r: Math.round(r * 255),
      g: Math.round(g * 255),
      b: Math.round(b * 255)
    };
  }

  /**
   * Pre-compiles categorical colors and degree-attenuated lightness for zero GC per frame.
   */
  function compileNodeColors(nodes, colorMode = "leiden") {
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      const deg = n.degree || 0;
      const comm = n.community !== undefined && n.community !== null
        ? n.community
        : (n.data && n.data.community !== undefined ? n.data.community : -1);

      let baseHex;
      if (colorMode === "degree") {
        // Degree centrality heatmap gradient: Cyan -> Emerald -> Amber -> Coral
        const t = Math.min(1.0, deg / 8.0);
        const hue = Math.round(195 - t * 180);
        const rgb = hslToRgb(hue < 0 ? hue + 360 : hue, 85, 58);
        baseHex = rgbToHex(rgb.r, rgb.g, rgb.b);
      } else if (colorMode === "tag" && n.data && (n.data.tags || n.data.type)) {
        const tag = (Array.isArray(n.data.tags) && n.data.tags[0]) || n.data.type || "default";
        let hash = 0;
        for (let ch = 0; ch < tag.length; ch++) hash = (hash * 31 + tag.charCodeAt(ch)) | 0;
        const idx = Math.abs(hash) % (DEFAULT_SEMANTIC_PALETTE.length - 1);
        baseHex = DEFAULT_SEMANTIC_PALETTE[idx];
      } else {
        // Default: Leiden Community Partitioning
        let commIdx = typeof comm === "number" ? comm : parseInt(comm);
        if (isNaN(commIdx) || commIdx < 0) {
          baseHex = NEUTRAL_LEAF_COLOR;
        } else if (commIdx < 5) {
          baseHex = DEFAULT_SEMANTIC_PALETTE[commIdx];
        } else {
          // Equidistant Golden Ratio HSL distribution for >= 5 clusters
          const hue = Math.round((commIdx * 137.507764) % 360);
          const rgb = hslToRgb(hue, 78, 62);
          baseHex = rgbToHex(rgb.r, rgb.g, rgb.b);
        }
      }

      n.categoryColor = baseHex;
      const rgb = hexToRgb(baseHex);
      const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);

      // Centrality Luminance Attenuation:
      // Base leaf nodes render with 40% alpha in their categorical color
      if (deg <= 1) {
        n.radius = deg === 0 ? 2.5 : 3.0;
        n.fillColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.40)`;
        n.auraColor = null;
        n.activeColor = baseHex;
        n.activeAuraColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.35)`;
        n.neighborColor = `rgb(${rgb.r}, ${rgb.g}, ${rgb.b})`;
      } else {
        // Hub nodes scale their radius: r = 3px + min(5, ln(degree + 1))
        n.radius = 3.0 + Math.min(5.0, Math.log(deg + 1));
        const lBoost = Math.min(20, Math.log(deg + 1) * 4);
        const modulatedL = Math.min(88, hsl.l + lBoost);
        const modulatedS = Math.min(100, hsl.s + Math.min(14, Math.log(deg + 1) * 3));
        const modRgb = hslToRgb(hsl.h, modulatedS, modulatedL);

        // Hub nodes receive higher saturation & subtle colored radial perimeter glow
        const restingAlpha = Math.min(0.85, 0.60 + Math.min(0.25, deg * 0.05));
        n.fillColor = `rgba(${modRgb.r}, ${modRgb.g}, ${modRgb.b}, ${restingAlpha.toFixed(2)})`;

        n.auraRadius = n.radius + 4.0 + Math.min(3.0, Math.log(deg));
        n.auraColor = `rgba(${modRgb.r}, ${modRgb.g}, ${modRgb.b}, 0.20)`;

        n.activeColor = `rgb(${modRgb.r}, ${modRgb.g}, ${modRgb.b})`;
        n.activeAuraColor = `rgba(${modRgb.r}, ${modRgb.g}, ${modRgb.b}, 0.40)`;

        const lightRgb = hslToRgb(hsl.h, Math.min(100, hsl.s + 10), Math.min(92, modulatedL + 12));
        n.neighborColor = `rgb(${lightRgb.r}, ${lightRgb.g}, ${lightRgb.b})`;
      }
    }
  }

  /* ============================================================
     2. 2D QUADTREE SPATIAL INDEX (Instantaneous O(log n) Hit-Testing)
     ============================================================ */
  class GalaxyQuadtree {
    constructor(bounds, maxPoints = 8, maxDepth = 10, depth = 0) {
      this.bounds = bounds; // { x, y, width, height }
      this.maxPoints = maxPoints;
      this.maxDepth = maxDepth;
      this.depth = depth;
      this.points = [];
      this.divided = false;
      this.nw = null;
      this.ne = null;
      this.sw = null;
      this.se = null;
    }

    subdivide() {
      const x = this.bounds.x;
      const y = this.bounds.y;
      const w = this.bounds.width / 2;
      const h = this.bounds.height / 2;
      const nextDepth = this.depth + 1;

      this.nw = new GalaxyQuadtree({ x: x, y: y, width: w, height: h }, this.maxPoints, this.maxDepth, nextDepth);
      this.ne = new GalaxyQuadtree({ x: x + w, y: y, width: w, height: h }, this.maxPoints, this.maxDepth, nextDepth);
      this.sw = new GalaxyQuadtree({ x: x, y: y + h, width: w, height: h }, this.maxPoints, this.maxDepth, nextDepth);
      this.se = new GalaxyQuadtree({ x: x + w, y: y + h, width: w, height: h }, this.maxPoints, this.maxDepth, nextDepth);
      this.divided = true;

      const oldPoints = this.points;
      this.points = [];
      for (let i = 0; i < oldPoints.length; i++) {
        this.insert(oldPoints[i]);
      }
    }

    contains(point) {
      return (
        point.x >= this.bounds.x &&
        point.x <= this.bounds.x + this.bounds.width &&
        point.y >= this.bounds.y &&
        point.y <= this.bounds.y + this.bounds.height
      );
    }

    insert(point) {
      if (!this.contains(point)) {
        return false;
      }

      if (this.points.length < this.maxPoints || this.depth >= this.maxDepth) {
        this.points.push(point);
        return true;
      }

      if (!this.divided) {
        this.subdivide();
      }

      return (
        this.nw.insert(point) ||
        this.ne.insert(point) ||
        this.sw.insert(point) ||
        this.se.insert(point)
      );
    }

    findNearest(qx, qy, maxRadius) {
      let bestPoint = null;
      let bestDistSq = maxRadius * maxRadius;

      function search(node) {
        const b = node.bounds;
        const closestX = Math.max(b.x, Math.min(qx, b.x + b.width));
        const closestY = Math.max(b.y, Math.min(qy, b.y + b.height));
        const dx = qx - closestX;
        const dy = qy - closestY;
        if (dx * dx + dy * dy > bestDistSq) {
          return;
        }

        for (let i = 0; i < node.points.length; i++) {
          const pt = node.points[i];
          const d2 = (qx - pt.x) * (qx - pt.x) + (qy - pt.y) * (qy - pt.y);
          if (d2 <= bestDistSq) {
            bestDistSq = d2;
            bestPoint = pt;
          }
        }

        if (node.divided) {
          search(node.nw);
          search(node.ne);
          search(node.sw);
          search(node.se);
        }
      }

      search(this);
      return bestPoint;
    }

    queryRadius(qx, qy, radius, out = []) {
      const r2 = radius * radius;
      function search(node) {
        if (!node) return;
        const b = node.bounds;
        const closestX = Math.max(b.x, Math.min(qx, b.x + b.width));
        const closestY = Math.max(b.y, Math.min(qy, b.y + b.height));
        const dx = qx - closestX;
        const dy = qy - closestY;
        if (dx * dx + dy * dy > r2) {
          return;
        }

        for (let i = 0; i < node.points.length; i++) {
          const pt = node.points[i];
          const d2 = (qx - pt.x) * (qx - pt.x) + (qy - pt.y) * (qy - pt.y);
          if (d2 <= r2) {
            out.push(pt);
          }
        }

        if (node.divided) {
          search(node.nw);
          search(node.ne);
          search(node.sw);
          search(node.se);
        }
      }

      search(this);
      return out;
    }
  }

  /* ============================================================
     3. BARNES-HUT QUADTREE & STANDALONE PHYSICS ENGINE
     ============================================================ */
  class BHNode {
    constructor(x, y, size) {
      this.x = x;
      this.y = y;
      this.size = size;
      this.mass = 0;
      this.cx = 0;
      this.cy = 0;
      this.bodyIndex = -1;
      this.children = null;
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
        new BHNode(this.x - quarter, this.y - quarter, half),
        new BHNode(this.x + quarter, this.y - quarter, half),
        new BHNode(this.x - quarter, this.y + quarter, half),
        new BHNode(this.x + quarter, this.y + quarter, half)
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
          const force = (kRepel * this.mass) / (distSq + 30.0);
          forces.fx += (dx / dist) * force;
          forces.fy += (dy / dist) * force;
        } else {
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

      this.edgeSrc = new Int32Array(0);
      this.edgeTgt = new Int32Array(0);
      this.edgeRest = new Float32Array(0);
      this.edgeWeight = new Float32Array(0);

      this.gridCellSize = 40;
      this.spatialGrid = new Map();

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

            // Displace surrounding node out of collision zone
            this.posX[j] += nx * overlap;
            this.posY[j] += ny * overlap;
            this.baseX[j] = this.posX[j];
            this.baseY[j] = this.posY[j];

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

      this.forcesX.fill(0);
      this.forcesY.fill(0);

      // 1. Barnes-Hut Quadtree Construction
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

        // Weak center gravity
        this.forcesX[i] -= this.posX[i] * kCenter * this.mass[i];
        this.forcesY[i] -= this.posY[i] * kCenter * this.mass[i];

        // Gentle baseline elastic restoring force toward baseline coordinates
        const kBase = 0.025;
        this.forcesX[i] -= (this.posX[i] - this.baseX[i]) * kBase * this.mass[i];
        this.forcesY[i] -= (this.posY[i] - this.baseY[i]) * kBase * this.mass[i];
        this.baseX[i] += (this.posX[i] - this.baseX[i]) * 0.008;
        this.baseY[i] += (this.posY[i] - this.baseY[i]) * 0.008;

        // Radial boundary falloff dampener
        const rDist = Math.hypot(this.posX[i], this.posY[i]);
        if (rDist > boundaryRadius) {
          const excess = rDist - boundaryRadius;
          const bF = excess * 0.06;
          this.forcesX[i] -= (this.posX[i] / rDist) * bF;
          this.forcesY[i] -= (this.posY[i] / rDist) * bF;
        }

        // Acceleration scaled by temperature
        const ax = (this.forcesX[i] / this.mass[i]) * alpha;
        const ay = (this.forcesY[i] / this.mass[i]) * alpha;

        // Semi-implicit Euler integration with velocity damping
        this.velX[i] = (this.velX[i] + ax) * damping;
        this.velY[i] = (this.velY[i] + ay) * damping;

        // Velocity clamping
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

      for (let i = 0; i < N; i++) {
        const gx = Math.floor(this.posX[i] / cellSize);
        const gy = Math.floor(this.posY[i] / cellSize);
        const p1Pinned = this.pinned[i];
        const r1 = this.collisionRadius[i];
        const m1 = this.mass[i];

        for (let ox = -1; ox <= 1; ox++) {
          for (let oy = -1; oy <= 1; oy++) {
            const key = `${gx + ox},${gy + oy}`;
            const cell = grid.get(key);
            if (!cell) continue;

            for (let c = 0; c < cell.length; c++) {
              const j = cell[c];
              if (i >= j) continue;

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
     4. HYBRID CONCENTRIC / SUNFLOWER PHYLLOTAXIS LAYOUT (Initial Placement)
     ============================================================ */
  function computeGalaxyLayout(nodes, edges, options = {}) {
    if (!nodes || nodes.length === 0) return {};
    if (nodes.length === 1) {
      const id = nodes[0].data ? nodes[0].data.id : nodes[0].id;
      return { [id]: { x: 0, y: 0 } };
    }

    const scale = options.scale || 800;
    const rCore = options.rCore || scale * 0.32;

    const degreeMap = new Map();
    const neighborMap = new Map();
    for (const n of nodes) {
      const id = n.data ? n.data.id : n.id;
      degreeMap.set(id, n.data && typeof n.data.degree === "number" ? n.data.degree : 0);
      neighborMap.set(id, new Set());
    }

    if (edges) {
      for (const e of edges) {
        const u = e.data ? e.data.source : e.source;
        const v = e.data ? e.data.target : e.target;
        if (neighborMap.has(u) && neighborMap.has(v)) {
          neighborMap.get(u).add(v);
          neighborMap.get(v).add(u);
        }
      }
    }

    for (const [id, nbs] of neighborMap.entries()) {
      if (!degreeMap.get(id)) {
        degreeMap.set(id, nbs.size);
      }
    }

    let coreNodes = [];
    let peripheralNodes = [];
    for (const n of nodes) {
      const id = n.data ? n.data.id : n.id;
      const deg = degreeMap.get(id) || 0;
      if (deg >= 2) coreNodes.push(n);
      else peripheralNodes.push(n);
    }

    if (coreNodes.length < 2 && nodes.length > 3) {
      const sorted = [...nodes].sort((a, b) => (degreeMap.get(b.data?.id || b.id) || 0) - (degreeMap.get(a.data?.id || a.id) || 0));
      const splitIdx = Math.max(2, Math.floor(nodes.length * 0.35));
      coreNodes = sorted.slice(0, splitIdx);
      peripheralNodes = sorted.slice(splitIdx);
    } else if (peripheralNodes.length === 0 && nodes.length > 12) {
      const sorted = [...nodes].sort((a, b) => (degreeMap.get(b.data?.id || b.id) || 0) - (degreeMap.get(a.data?.id || a.id) || 0));
      const splitIdx = Math.max(6, Math.floor(nodes.length * 0.5));
      coreNodes = sorted.slice(0, splitIdx);
      peripheralNodes = sorted.slice(splitIdx);
    }

    const positions = {};

    if (coreNodes.length > 0) {
      const cCount = coreNodes.length;
      const cPositions = new Map();
      const coreIds = new Set(coreNodes.map((n) => (n.data ? n.data.id : n.id)));

      for (let i = 0; i < cCount; i++) {
        const id = coreNodes[i].data ? coreNodes[i].data.id : coreNodes[i].id;
        const pos = coreNodes[i].position;
        if (pos && typeof pos.x === "number" && typeof pos.y === "number") {
          cPositions.set(id, { x: pos.x, y: pos.y, vx: 0, vy: 0 });
        } else {
          const ang = (i / cCount) * Math.PI * 2;
          const rad = Math.random() * rCore * 0.7;
          cPositions.set(id, { x: Math.cos(ang) * rad, y: Math.sin(ang) * rad, vx: 0, vy: 0 });
        }
      }

      const steps = Math.min(100, Math.max(40, options.iterations || 80));
      const cList = Array.from(cPositions.entries());
      for (let step = 0; step < steps; step++) {
        const temp = 1.0 - step / steps;
        for (let i = 0; i < cList.length; i++) {
          const [idA, pA] = cList[i];
          let fx = 0, fy = 0;

          for (let j = i + 1; j < cList.length; j++) {
            const [idB, pB] = cList[j];
            const dx = pB.x - pA.x;
            const dy = pB.y - pA.y;
            const distSq = dx * dx + dy * dy || 1.0;
            if (distSq < rCore * rCore) {
              const dist = Math.sqrt(distSq);
              const rep = 600 / (distSq + 10);
              const rx = (dx / dist) * rep;
              const ry = (dy / dist) * rep;
              fx -= rx;
              fy -= ry;
              pB.vx += rx;
              pB.vy += ry;
            }
          }

          const nbs = neighborMap.get(idA);
          if (nbs) {
            for (const nbId of nbs) {
              if (coreIds.has(nbId)) {
                const pB = cPositions.get(nbId);
                if (pB) {
                  const dx = pB.x - pA.x;
                  const dy = pB.y - pA.y;
                  const dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
                  const disp = dist - 70;
                  const spring = disp * 0.04;
                  fx += (dx / dist) * spring;
                  fy += (dy / dist) * spring;
                }
              }
            }
          }

          fx -= pA.x * 0.003;
          fy -= pA.y * 0.003;

          pA.vx = (pA.vx + fx) * 0.82;
          pA.vy = (pA.vy + fy) * 0.82;
          pA.x += pA.vx * temp;
          pA.y += pA.vy * temp;
        }
      }

      let maxDist = 1;
      for (const [, p] of cPositions.entries()) {
        const d = Math.hypot(p.x, p.y);
        if (d > maxDist) maxDist = d;
      }
      const rescale = (rCore * 0.9) / Math.max(maxDist, 1);
      for (const [id, p] of cPositions.entries()) {
        positions[id] = {
          x: Math.round(p.x * rescale),
          y: Math.round(p.y * rescale)
        };
      }
    }

    if (peripheralNodes.length > 0) {
      const connected = [];
      const isolated = [];

      for (const n of peripheralNodes) {
        const id = n.data ? n.data.id : n.id;
        const nbs = neighborMap.get(id);
        let parentPos = null;
        if (nbs) {
          for (const nbId of nbs) {
            if (positions[nbId]) {
              parentPos = positions[nbId];
              break;
            }
          }
        }

        if (parentPos) {
          const ang = Math.atan2(parentPos.y, parentPos.x);
          connected.push({ node: n, id, angle: ang });
        } else {
          isolated.push({ node: n, id, angle: 0 });
        }
      }

      connected.sort((a, b) => a.angle - b.angle);
      const allOuter = connected.concat(isolated);

      const nOuter = allOuter.length;
      const rMax = scale;
      const cStep = (rMax - rCore) / Math.max(Math.sqrt(nOuter), 1);

      for (let i = 0; i < nOuter; i++) {
        const item = allOuter[i];
        const nIdx = i + 1;
        let theta = nIdx * GOLDEN_ANGLE_RAD;
        const r = rCore + cStep * Math.sqrt(nIdx);

        if (i < connected.length) {
          const parentAngle = connected[i].angle;
          theta = parentAngle + ((i % 5) - 2) * 0.22;
        }

        positions[item.id] = {
          x: Math.round(r * Math.cos(theta)),
          y: Math.round(r * Math.sin(theta))
        };
      }
    }

    return positions;
  }

  /* ============================================================
     5. OBSIDIAN GALAXY ENGINE (DUAL-CANVAS 2D VISUALIZATION ENGINE)
     ============================================================ */
  class ObsidianGalaxyEngine {
    constructor(container, options = {}) {
      if (typeof container === "string") {
        container = document.querySelector(container);
      }
      if (!container) {
        throw new Error("ObsidianGalaxyEngine requires a valid DOM container element.");
      }
      this.container = container;
      this.options = Object.assign(
        {
          backgroundColor: "#0d1117",
          edgeBaseColor: "rgba(255, 255, 255, 0.06)",
          minScale: 0.1,
          maxScale: 6.0,
          hitRadius: 12,
          useWorker: true,
          physicsOptions: {},
          onNodeClick: null,
          onNodeHover: null,
          onNodeDragStart: null,
          onNodeDrag: null,
          onNodeDragEnd: null
        },
        options
      );

      this.nodes = [];
      this.edges = [];
      this.nodeMap = new Map();
      this.adjacency = new Map();
      this.incidentEdges = new Map();
      this.quadtree = null;

      this.width = 0;
      this.height = 0;
      this.dpr = window.devicePixelRatio || 1;

      // Viewport transform
      this.transform = {
        panX: 0,
        panY: 0,
        scale: 1.0
      };
      this.savedCoordinates = new Map();
      this.hasFittedOnce = false;

      // Interaction & Physics state
      this.isPanning = false;
      this.isDraggingNode = false;
      this.draggedNode = null;
      this.dragOffset = { x: 0, y: 0 };
      this.nodeDragStartPos = { x: 0, y: 0 };
      this.hasDraggedNodeMoved = false;
      this.hasPanned = false;
      this.justFinishedDrag = false;
      this.dragStart = { x: 0, y: 0 };
      this.dragHistory = []; // Circular velocity buffer for momentum fling

      this.activeNode = null;
      this.hoveredNode = null;
      this.rafPending = false;
      this.interactiveRafPending = false;
      this.frameCount = 0;

      // Physics worker & fallback
      this.worker = null;
      this.fallbackEngine = null;
      this.isPhysicsRunning = false;
      this.fallbackRaf = null;

      // Screen-wide ambient pointer tracking & force field
      this.ambientPointer = {
        active: false,
        clientX: 0,
        clientY: 0,
        screenX: 0,
        screenY: 0,
        worldX: 0,
        worldY: 0,
        lastTime: 0
      };
      this.ambientRafPending = false;
      this._hasBoundGlobalPointer = false;

      this.initDom();
      this.initWorker();
      this.bindEvents();
      this.initGlobalAmbientPointerTracking();
    }

    initDom() {
      this.container.style.position = "relative";
      this.container.style.overflow = "hidden";
      this.container.style.backgroundColor = this.options.backgroundColor;

      // Layer 1: Background Canvas (nodes, hub auras, hairline edges)
      this.bgCanvas = document.createElement("canvas");
      this.bgCanvas.id = "galaxy-bg-canvas";
      this.bgCanvas.className = "galaxy-canvas galaxy-bg-canvas";
      this.bgCanvas.style.position = "absolute";
      this.bgCanvas.style.top = "0";
      this.bgCanvas.style.left = "0";
      this.bgCanvas.style.width = "100%";
      this.bgCanvas.style.height = "100%";
      this.bgCanvas.style.display = "block";
      this.bgCanvas.style.zIndex = "1";
      this.bgCanvas.style.pointerEvents = "none";
      this.bgCtx = this.bgCanvas.getContext("2d");

      // Layer 2: Interactive Canvas (starburst spotlight, glowing edges, monospaced pill, dragging)
      this.interactiveCanvas = document.createElement("canvas");
      this.interactiveCanvas.id = "galaxy-canvas";
      this.interactiveCanvas.className = "galaxy-canvas galaxy-interactive-canvas";
      this.interactiveCanvas.style.position = "absolute";
      this.interactiveCanvas.style.top = "0";
      this.interactiveCanvas.style.left = "0";
      this.interactiveCanvas.style.width = "100%";
      this.interactiveCanvas.style.height = "100%";
      this.interactiveCanvas.style.display = "block";
      this.interactiveCanvas.style.zIndex = "2";
      this.interactiveCanvas.style.cursor = "default";
      this.interactiveCtx = this.interactiveCanvas.getContext("2d");

      this.container.appendChild(this.bgCanvas);
      this.container.appendChild(this.interactiveCanvas);

      const hasCanvas = !!document.getElementById("galaxy-canvas");
      console.log(`[Graph Engine] Canvas element found: ${hasCanvas}`);
      console.log(`[Graph Engine] Canvas client dimensions: ${this.container.clientWidth}x${this.container.clientHeight}`);

      this.resize();
    }

    initWorker() {
      if (this.options.useWorker && typeof window !== "undefined" && window.Worker) {
        try {
          this.worker = new Worker("/static/assets/js/physics.worker.js");
          this.worker.onmessage = (e) => this.handleWorkerMessage(e.data);
          this.worker.onerror = (err) => {
            console.warn("Physics worker failed, falling back to direct engine:", err);
            this.worker = null;
            this.ensureFallbackEngine();
          };
        } catch (e) {
          console.warn("Cannot instantiate physics worker, using direct engine:", e);
          this.worker = null;
          this.ensureFallbackEngine();
        }
      } else {
        this.ensureFallbackEngine();
      }
    }

    ensureFallbackEngine() {
      if (!this.fallbackEngine) {
        this.fallbackEngine = new PhysicsEngine(this.options.physicsOptions);
      }
    }

    handleWorkerMessage(data) {
      if (!data) return;

      if (data.type === "tick" || data.type === "step_result" || data.type === "sleep") {
        if (data.positions) {
          const flat = new Float32Array(data.positions);
          const N = this.nodes.length;
          for (let i = 0; i < N; i++) {
            const n = this.nodes[i];
            n.x = flat[i * 2];
            n.y = flat[i * 2 + 1];
            this.savedCoordinates.set(n.id, { x: n.x, y: n.y });
            if (n.data && typeof n.data === "object") {
              if (!n.data.position) n.data.position = { x: n.x, y: n.y };
              else { n.data.position.x = n.x; n.data.position.y = n.y; }
            }
          }
        }

        if (data.type === "sleep") {
          this.isPhysicsRunning = false;
          this.rebuildQuadtree();
        } else {
          this.isPhysicsRunning = true;
        }

        this.drawBackground();
        if (this.hoveredNode || this.activeNode) {
          this.drawInteractive();
        }
      }
    }

    runFallbackLoop() {
      if (!this.fallbackEngine || !this.fallbackEngine.isRunning) return;
      if (this.fallbackRaf) return;

      const tick = () => {
        this.fallbackRaf = null;
        if (!this.fallbackEngine || !this.fallbackEngine.isRunning) {
          this.isPhysicsRunning = false;
          this.rebuildQuadtree();
          this.drawBackground();
          return;
        }

        const res = this.fallbackEngine.step();
        const N = this.nodes.length;
        for (let i = 0; i < N; i++) {
          const n = this.nodes[i];
          n.x = this.fallbackEngine.posX[i];
          n.y = this.fallbackEngine.posY[i];
          this.savedCoordinates.set(n.id, { x: n.x, y: n.y });
          if (n.data && typeof n.data === "object") {
            if (!n.data.position) n.data.position = { x: n.x, y: n.y };
            else { n.data.position.x = n.x; n.data.position.y = n.y; }
          }
        }

        this.isPhysicsRunning = !res.sleeping;
        this.drawBackground();
        if (this.hoveredNode || this.activeNode) {
          this.drawInteractive();
        }

        if (this.fallbackEngine.isRunning) {
          this.fallbackRaf = requestAnimationFrame(tick);
        } else {
          this.rebuildQuadtree();
        }
      };

      this.fallbackRaf = requestAnimationFrame(tick);
    }

    resize(explicitWidth, explicitHeight, forceFit = false) {
      const rect = this.container.getBoundingClientRect();
      const newWidth = Math.floor(explicitWidth !== undefined ? explicitWidth : rect.width);
      const newHeight = Math.floor(explicitHeight !== undefined ? explicitHeight : rect.height);
      if (newWidth < 50 || newHeight < 50) return;

      const deltaW = Math.abs(newWidth - this.width);
      const deltaH = Math.abs(newHeight - this.height);
      if (deltaW <= 2 && deltaH <= 2 && !forceFit) return;

      const prevWidth = this.width;
      const prevHeight = this.height;

      this.width = newWidth;
      this.height = newHeight;
      this.dpr = window.devicePixelRatio || 1;

      const pxW = Math.floor(this.width * this.dpr);
      const pxH = Math.floor(this.height * this.dpr);

      if (this.bgCanvas.width !== pxW || this.bgCanvas.height !== pxH) {
        this.bgCanvas.width = pxW;
        this.bgCanvas.height = pxH;
      }
      if (this.interactiveCanvas.width !== pxW || this.interactiveCanvas.height !== pxH) {
        this.interactiveCanvas.width = pxW;
        this.interactiveCanvas.height = pxH;
      }

      if (prevWidth > 0 && prevHeight > 0 && !forceFit) {
        this.transform.panX += (this.width - prevWidth) / 2;
        this.transform.panY += (this.height - prevHeight) / 2;
        this.drawBackground();
        this.drawInteractive();
      } else if (forceFit || !this.hasFittedOnce) {
        this.fit();
        this.hasFittedOnce = true;
      } else {
        this.drawBackground();
        this.drawInteractive();
      }
    }

    setData(elements, forceLayout = false) {
      if (!elements) return;
      const rawNodes = elements.nodes || (Array.isArray(elements) ? elements.filter(e => !e.data || (!e.data.source && !e.data.target)) : []);
      const rawEdges = elements.edges || (Array.isArray(elements) ? elements.filter(e => e.data && e.data.source && e.data.target) : []);

      if (forceLayout) {
        this.savedCoordinates.clear();
      }

      // Adjacency for placing new incoming nodes next to connected nodes
      const edgeAdjacency = new Map();
      for (const re of rawEdges) {
        const u = re.data ? re.data.source : re.source;
        const v = re.data ? re.data.target : re.target;
        if (u && v) {
          if (!edgeAdjacency.has(u)) edgeAdjacency.set(u, []);
          if (!edgeAdjacency.has(v)) edgeAdjacency.set(v, []);
          edgeAdjacency.get(u).push(v);
          edgeAdjacency.get(v).push(u);
        }
      }

      const unplacedNodes = [];
      for (const rn of rawNodes) {
        const id = rn.data ? rn.data.id : rn.id;
        if (!this.savedCoordinates.has(id)) {
          if (rn.position && typeof rn.position.x === "number" && typeof rn.position.y === "number") {
            this.savedCoordinates.set(id, { x: rn.position.x, y: rn.position.y });
          } else {
            unplacedNodes.push(rn);
          }
        }
      }

      if (unplacedNodes.length > 0) {
        if (this.savedCoordinates.size === 0) {
          const computedLayout = computeGalaxyLayout(rawNodes, rawEdges, { scale: Math.min(this.width || 800, this.height || 600) * 0.95 });
          for (const [id, pos] of Object.entries(computedLayout)) {
            this.savedCoordinates.set(id, pos);
          }
        } else {
          const scale = Math.min(this.width || 800, this.height || 600) * 0.95;
          const rCore = scale * 0.32;
          let outerIdx = this.savedCoordinates.size + 1;

          for (const un of unplacedNodes) {
            const id = un.data ? un.data.id : un.id;
            const nbs = edgeAdjacency.get(id) || [];
            let placed = false;
            for (const nbId of nbs) {
              if (this.savedCoordinates.has(nbId)) {
                const parent = this.savedCoordinates.get(nbId);
                const angle = (outerIdx * GOLDEN_ANGLE_RAD) % (Math.PI * 2);
                const dist = 65 + Math.random() * 25;
                this.savedCoordinates.set(id, {
                  x: Math.round(parent.x + Math.cos(angle) * dist),
                  y: Math.round(parent.y + Math.sin(angle) * dist)
                });
                placed = true;
                break;
              }
            }
            if (!placed) {
              const theta = outerIdx * GOLDEN_ANGLE_RAD;
              const r = rCore + (scale - rCore) * 0.5 + Math.sqrt(outerIdx) * 12;
              this.savedCoordinates.set(id, {
                x: Math.round(r * Math.cos(theta)),
                y: Math.round(r * Math.sin(theta))
              });
            }
            outerIdx++;
          }
        }
      }

      this.nodes = [];
      this.edges = [];
      this.nodeMap.clear();
      this.adjacency.clear();
      this.incidentEdges.clear();

      for (let i = 0; i < rawNodes.length; i++) {
        const rn = rawNodes[i];
        const id = rn.data ? rn.data.id : rn.id;
        const pos = this.savedCoordinates.get(id) || (rn.position && typeof rn.position.x === "number" ? rn.position : { x: 0, y: 0 });
        const degree = (rn.data && typeof rn.data.degree === "number") ? rn.data.degree : 1;
        const label = (rn.data && rn.data.label) ? rn.data.label : (rn.label || id);
        const type = (rn.data && rn.data.type) ? rn.data.type : "ENTITY";
        const community = (rn.data && rn.data.community !== undefined) ? rn.data.community : (rn.community !== undefined ? rn.community : 0);

        // Radius: leaf nodes 2.5px-3px; hubs: 3px + min(5, ln(degree + 1))
        const radius = degree <= 1 ? (degree === 0 ? 2.5 : 3.0) : (3.0 + Math.min(5.0, Math.log(degree + 1)));

        const node = {
          id,
          x: pos.x,
          y: pos.y,
          radius,
          degree,
          label,
          type,
          community,
          data: rn.data || rn
        };

        this.nodes.push(node);
        this.nodeMap.set(id, node);
        this.adjacency.set(id, new Set());
        this.incidentEdges.set(id, []);
      }

      for (let j = 0; j < rawEdges.length; j++) {
        const re = rawEdges[j];
        const id = re.data ? re.data.id : (re.id || `${re.source}_${re.target}`);
        const source = re.data ? re.data.source : re.source;
        const target = re.data ? re.data.target : re.target;
        const label = re.data ? re.data.label : (re.label || "relates");
        const weight = re.data ? (re.data.weight || 1.0) : 1.0;

        const srcNode = this.nodeMap.get(source);
        const tgtNode = this.nodeMap.get(target);

        if (srcNode && tgtNode) {
          const edge = {
            id,
            source,
            target,
            sourceNode: srcNode,
            targetNode: tgtNode,
            label,
            weight,
            data: re.data || re
          };
          this.edges.push(edge);
          this.adjacency.get(source).add(target);
          this.adjacency.get(target).add(source);
          this.incidentEdges.get(source).push(edge);
          this.incidentEdges.get(target).push(edge);
        }
      }

      // Pre-compile categorical color schemes & luminance attenuation
      compileNodeColors(this.nodes, this.options.colorMode || "leiden");

      // Initialize Quadtree for hit-testing
      this.rebuildQuadtree();

      // Only auto-fit viewport on initial mount or forced re-layout
      if (!this.hasFittedOnce || forceLayout) {
        this.fit();
        this.hasFittedOnce = true;
      } else {
        this.drawBackground();
        this.drawInteractive();
      }

      // Empty-State Guard: If no nodes, stop physics immediately and render zero-state
      if (this.nodes.length === 0) {
        console.log("[Graph Engine] Initialized with 0 nodes");
        if (this.worker) {
          this.worker.postMessage({ type: "stop" });
        } else if (this.fallbackEngine) {
          this.fallbackEngine.isRunning = false;
        }
        this.isPhysicsRunning = false;
        this.drawBackground();
        this.drawInteractive();
        return;
      }

      console.log(`[Graph Engine] Initialized with ${this.nodes.length} nodes`);

      // Launch Real-Time Force Physics Engine
      if (this.worker) {
        this.worker.postMessage({
          type: "init",
          nodes: this.nodes.map(n => ({
            id: n.id,
            x: n.x,
            y: n.y,
            radius: n.radius,
            degree: n.degree
          })),
          edges: this.edges.map(e => ({
            source: e.source,
            target: e.target,
            weight: e.weight
          })),
          options: this.options.physicsOptions
        });
        this.isPhysicsRunning = true;
      } else {
        this.ensureFallbackEngine();
        this.fallbackEngine.init(this.nodes, this.edges, this.options.physicsOptions);
        this.fallbackEngine.wake(1.0);
        this.isPhysicsRunning = true;
      }
    }

    fit(padding = 50) {
      if (this.nodes.length === 0) {
        this.transform.panX = this.width / 2;
        this.transform.panY = this.height / 2;
        this.transform.scale = 1.0;
        this.drawBackground();
        return;
      }

      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (let i = 0; i < this.nodes.length; i++) {
        const n = this.nodes[i];
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      }

      const gw = maxX - minX || 1;
      const gh = maxY - minY || 1;
      const availW = Math.max(this.width - padding * 2, 80);
      const availH = Math.max(this.height - padding * 2, 80);

      const scale = Math.min(availW / gw, availH / gh, 1.4);
      const clampedScale = Math.max(this.options.minScale, Math.min(this.options.maxScale, scale));

      const cx = (minX + maxX) / 2;
      const cy = (minY + maxY) / 2;

      this.transform.scale = clampedScale;
      this.transform.panX = this.width / 2 - cx * clampedScale;
      this.transform.panY = this.height / 2 - cy * clampedScale;

      this.drawBackground();
      this.drawInteractive();
    }

    screenToWorld(sx, sy) {
      return {
        x: (sx - this.transform.panX) / this.transform.scale,
        y: (sy - this.transform.panY) / this.transform.scale
      };
    }

    worldToScreen(wx, wy) {
      return {
        x: wx * this.transform.scale + this.transform.panX,
        y: wy * this.transform.scale + this.transform.panY
      };
    }

    findNodeAt(sx, sy) {
      if (!this.quadtree || this.nodes.length === 0) return null;
      const worldPos = this.screenToWorld(sx, sy);
      const searchRad = Math.max(this.options.hitRadius + 8, 26) / this.transform.scale;
      const nearest = this.quadtree.findNearest(worldPos.x, worldPos.y, searchRad);
      if (!nearest) return null;

      const screenDist = Math.hypot(
        (nearest.x - worldPos.x) * this.transform.scale,
        (nearest.y - worldPos.y) * this.transform.scale
      );
      const hitThreshold = Math.max(nearest.radius * this.transform.scale + 10, 18);
      if (screenDist <= hitThreshold) {
        return nearest;
      }
      return null;
    }

    rebuildQuadtree() {
      if (this.nodes.length > 0) {
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        for (let i = 0; i < this.nodes.length; i++) {
          const n = this.nodes[i];
          if (n.x < minX) minX = n.x;
          if (n.x > maxX) maxX = n.x;
          if (n.y < minY) minY = n.y;
          if (n.y > maxY) maxY = n.y;
        }
        const margin = 200;
        const qBounds = {
          x: minX - margin,
          y: minY - margin,
          width: Math.max(maxX - minX + margin * 2, 200),
          height: Math.max(maxY - minY + margin * 2, 200)
        };
        this.quadtree = new GalaxyQuadtree(qBounds, 8, 12);
        for (let i = 0; i < this.nodes.length; i++) {
          this.quadtree.insert(this.nodes[i]);
        }
      } else {
        this.quadtree = null;
      }
    }

    /* ============================================================
       BACKGROUND DRAWING (Hairline Edges, Hub Auras, Categorical Dots)
       ============================================================ */
    drawBackground() {
      if (this.rafPending) return;
      this.rafPending = true;
      requestAnimationFrame(() => {
        this.rafPending = false;
        this.frameCount = (this.frameCount || 0) + 1;
        if (this.frameCount <= 3 || this.frameCount % 60 === 0) {
          console.log(`[Graph Engine] Render loop ticking: frame ${this.frameCount}`);
        }
        const ctx = this.bgCtx;
        const dpr = this.dpr;

        // Reset and fill with deep slate galaxy background
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.fillStyle = this.options.backgroundColor;
        ctx.fillRect(0, 0, this.bgCanvas.width, this.bgCanvas.height);

        // Empty Canvas Guard: When note count is 0
        if (this.nodes.length === 0) {
          ctx.font = `${Math.round(13 * dpr)}px Inter, sans-serif`;
          ctx.fillStyle = "#64748b";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(
            "No notes yet. Click 'Add Note' to start building your graph.",
            this.bgCanvas.width / 2,
            this.bgCanvas.height / 2
          );
          return;
        }

        // Apply viewport matrix transform
        ctx.setTransform(
          dpr * this.transform.scale,
          0,
          0,
          dpr * this.transform.scale,
          dpr * this.transform.panX,
          dpr * this.transform.panY
        );

        // 1. Subtle hairline strokes for inactive edges (0.5px - 1px)
        ctx.lineWidth = 0.75 / this.transform.scale;
        ctx.strokeStyle = this.options.edgeBaseColor;
        ctx.beginPath();
        for (let i = 0; i < this.edges.length; i++) {
          const e = this.edges[i];
          ctx.moveTo(e.sourceNode.x, e.sourceNode.y);
          ctx.lineTo(e.targetNode.x, e.targetNode.y);
        }
        ctx.stroke();

        // 2. Hub perimeter auras for higher centrality concepts
        for (let i = 0; i < this.nodes.length; i++) {
          const n = this.nodes[i];
          if (n.auraColor) {
            ctx.fillStyle = n.auraColor;
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.auraRadius, 0, Math.PI * 2);
            ctx.fill();
          }
        }

        // 3. Categorical node dots with degree luminance
        for (let i = 0; i < this.nodes.length; i++) {
          const n = this.nodes[i];
          ctx.fillStyle = n.fillColor || "rgba(200, 205, 215, 0.40)";
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
          ctx.fill();
        }
      });
    }

    /* ============================================================
       INTERACTIVE DRAWING (Starburst Effect, Radiant Glow & Monospaced Pill)
       ============================================================ */
    drawInteractive() {
      if (this.interactiveRafPending) return;
      this.interactiveRafPending = true;
      requestAnimationFrame(() => {
        this.interactiveRafPending = false;
        const ctx = this.interactiveCtx;
        const dpr = this.dpr;

        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, this.interactiveCanvas.width, this.interactiveCanvas.height);

        const target = this.hoveredNode || this.activeNode;
        if (!target) return;

        ctx.setTransform(
          dpr * this.transform.scale,
          0,
          0,
          dpr * this.transform.scale,
          dpr * this.transform.panX,
          dpr * this.transform.panY
        );

        const neighbors = this.adjacency.get(target.id) || new Set();
        const incEdges = this.incidentEdges.get(target.id) || [];
        const accentColor = target.activeColor || "#38bdf8";

        // 1. Direct incoming/outgoing edges illuminated into color-matched vector lines (1.5px, 85% opacity)
        ctx.save();
        ctx.lineWidth = 1.5 / this.transform.scale;
        ctx.strokeStyle = accentColor;
        ctx.globalAlpha = 0.85;
        ctx.shadowBlur = 8;
        ctx.shadowColor = accentColor;
        ctx.beginPath();
        for (let i = 0; i < incEdges.length; i++) {
          const e = incEdges[i];
          ctx.moveTo(e.sourceNode.x, e.sourceNode.y);
          ctx.lineTo(e.targetNode.x, e.targetNode.y);
        }
        ctx.stroke();
        ctx.restore();

        // 2. 1-hop adjacent nodes light up with their categorical neighbor colors
        ctx.save();
        for (const nbId of neighbors) {
          const nbNode = this.nodeMap.get(nbId);
          if (nbNode && nbNode !== target) {
            ctx.fillStyle = nbNode.neighborColor || "#bae6fd";
            ctx.shadowBlur = 6;
            ctx.shadowColor = nbNode.categoryColor || accentColor;
            ctx.beginPath();
            const rad = nbNode.radius + 1.2;
            ctx.arc(nbNode.x, nbNode.y, rad, 0, Math.PI * 2);
            ctx.fill();
          }
        }
        ctx.restore();

        // 3. Target node illuminates in full luminance with radiant outer halo
        ctx.save();
        if (target.activeAuraColor) {
          ctx.fillStyle = target.activeAuraColor;
          ctx.beginPath();
          ctx.arc(target.x, target.y, target.radius + 5.0, 0, Math.PI * 2);
          ctx.fill();
        }

        ctx.fillStyle = target.activeColor || "#38bdf8";
        ctx.shadowBlur = 12;
        ctx.shadowColor = target.activeColor || "#38bdf8";
        ctx.beginPath();
        const activeRadius = target.radius + 2.5;
        ctx.arc(target.x, target.y, activeRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        // 3.5 Render glowing halos for all cited/highlighted nodes (e.g. from Voice RAG)
        if (this.highlightedNodeIds && this.highlightedNodeIds.size > 1) {
          ctx.save();
          for (const hid of this.highlightedNodeIds) {
            const hn = this.nodeMap.get(hid);
            if (hn && hn !== target) {
              ctx.fillStyle = hn.activeAuraColor || "rgba(56, 189, 248, 0.25)";
              ctx.beginPath();
              ctx.arc(hn.x, hn.y, hn.radius + 4.5, 0, Math.PI * 2);
              ctx.fill();

              ctx.fillStyle = hn.activeColor || "#38bdf8";
              ctx.shadowBlur = 10;
              ctx.shadowColor = "#38bdf8";
              ctx.beginPath();
              ctx.arc(hn.x, hn.y, hn.radius + 1.8, 0, Math.PI * 2);
              ctx.fill();
            }
          }
          ctx.restore();
        }

        // 4. Multi-line monospaced typography pill
        this.renderLabelPill(ctx, target, incEdges.length);
      });
    }

    renderLabelPill(ctx, target, edgeCount) {
      const screenPos = this.worldToScreen(target.x, target.y);

      ctx.save();
      ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);

      const title = String(target.label || target.id);
      const subtitle = `${target.type} · C${target.community} · degree ${target.degree || edgeCount} · ${edgeCount} links`;

      const fontTitle = "600 11px 'JetBrains Mono', 'Fira Code', monospace";
      const fontSub = "9.5px 'JetBrains Mono', 'Fira Code', monospace";

      ctx.font = fontTitle;
      const titleWidth = ctx.measureText(title).width;
      ctx.font = fontSub;
      const subWidth = ctx.measureText(subtitle).width;

      const textWidth = Math.max(titleWidth, subWidth);
      const paddingX = 10;
      const paddingY = 8;
      const pillWidth = textWidth + paddingX * 2;
      const pillHeight = 38;

      let pillX = screenPos.x + 14;
      let pillY = screenPos.y - pillHeight / 2;

      if (pillX + pillWidth > this.width - 10) {
        pillX = screenPos.x - pillWidth - 14;
      }
      if (pillY < 10) pillY = 10;
      if (pillY + pillHeight > this.height - 10) pillY = this.height - pillHeight - 10;

      const accentBorder = target.categoryColor ? `rgba(${hexToRgb(target.categoryColor).r}, ${hexToRgb(target.categoryColor).g}, ${hexToRgb(target.categoryColor).b}, 0.55)` : "rgba(56, 189, 248, 0.40)";

      ctx.fillStyle = "rgba(13, 17, 23, 0.92)";
      ctx.strokeStyle = accentBorder;
      ctx.lineWidth = 1.2;
      ctx.shadowBlur = 14;
      ctx.shadowColor = "rgba(0, 0, 0, 0.7)";

      const r = 6;
      ctx.beginPath();
      ctx.moveTo(pillX + r, pillY);
      ctx.lineTo(pillX + pillWidth - r, pillY);
      ctx.quadraticCurveTo(pillX + pillWidth, pillY, pillX + pillWidth, pillY + r);
      ctx.lineTo(pillX + pillWidth, pillY + pillHeight - r);
      ctx.quadraticCurveTo(pillX + pillWidth, pillY + pillHeight, pillX + pillWidth - r, pillY + pillHeight);
      ctx.lineTo(pillX + r, pillY + pillHeight);
      ctx.quadraticCurveTo(pillX, pillY + pillHeight, pillX, pillY + pillHeight - r);
      ctx.lineTo(pillX, pillY + r);
      ctx.quadraticCurveTo(pillX, pillY, pillX + r, pillY);
      ctx.closePath();
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.stroke();

      ctx.fillStyle = "#f8fafc";
      ctx.font = fontTitle;
      ctx.textBaseline = "top";
      ctx.fillText(title, pillX + paddingX, pillY + paddingY);

      ctx.fillStyle = "#94a3b8";
      ctx.font = fontSub;
      ctx.fillText(subtitle, pillX + paddingX, pillY + paddingY + 16);

      ctx.restore();
    }

    /* ============================================================
       EVENT HANDLING (Kinematic Pinning, Drag Fling, Pan & Zoom)
       ============================================================ */
    bindEvents() {
      const cvs = this.interactiveCanvas;

      cvs.addEventListener("mousemove", (e) => {
        const rect = cvs.getBoundingClientRect();
        const sx = e.clientX - rect.left;
        const sy = e.clientY - rect.top;

        // 1. Dragging Node (Kinematic Pinning)
        if (this.isDraggingNode && this.draggedNode) {
          const worldPos = this.screenToWorld(sx, sy);
          const newX = worldPos.x + this.dragOffset.x;
          const newY = worldPos.y + this.dragOffset.y;

          if (Math.hypot(newX - this.nodeDragStartPos.x, newY - this.nodeDragStartPos.y) > 2) {
            this.hasDraggedNodeMoved = true;
          }

          this.draggedNode.x = newX;
          this.draggedNode.y = newY;
          if (this.draggedNode.data && typeof this.draggedNode.data === "object") {
            this.draggedNode.data.position = { x: newX, y: newY };
          }

          // Record velocity history for momentum fling
          const now = performance.now();
          this.dragHistory.push({ x: newX, y: newY, time: now });
          if (this.dragHistory.length > 5) this.dragHistory.shift();

          // Push to physics engine
          if (this.worker) {
            this.worker.postMessage({ type: "drag_move", id: this.draggedNode.id, x: newX, y: newY });
          } else if (this.fallbackEngine) {
            this.fallbackEngine.setNodePosition(this.draggedNode.id, newX, newY, true, 0);
            this.fallbackEngine.resolveKinematicCollision(this.draggedNode.id);
            const N = this.fallbackEngine.nodeCount;
            for (let i = 0; i < N; i++) {
              const nid = this.fallbackEngine.nodeIds[i];
              const nd = this.nodeMap.get(nid);
              if (nd && nd !== this.draggedNode) {
                nd.x = this.fallbackEngine.posX[i];
                nd.y = this.fallbackEngine.posY[i];
              }
            }
          }

          cvs.style.cursor = "grabbing";
          this.drawBackground();
          this.drawInteractive();

          if (this.options.onNodeDrag) {
            this.options.onNodeDrag(this.draggedNode.data || this.draggedNode, newX, newY);
          }
          return;
        }

        // 2. Viewport Panning
        if (this.isPanning) {
          const dx = sx - this.dragStart.x;
          const dy = sy - this.dragStart.y;
          if (Math.hypot(dx, dy) > 2) {
            this.hasPanned = true;
          }
          this.transform.panX += dx;
          this.transform.panY += dy;
          this.dragStart.x = sx;
          this.dragStart.y = sy;
          cvs.style.cursor = "grabbing";
          this.drawBackground();
          this.drawInteractive();
          return;
        }

        // 3. Resting Hover Hit-Test: Strictly Quadtree hit-testing
        this.updateHoveredNode(e.clientX, e.clientY);
      });

      cvs.addEventListener("mousedown", (e) => {
        if (e.button !== 0) return;
        const rect = cvs.getBoundingClientRect();
        const sx = e.clientX - rect.left;
        const sy = e.clientY - rect.top;

        const hit = this.findNodeAt(sx, sy);
        if (hit) {
          const worldPos = this.screenToWorld(sx, sy);
          this.isDraggingNode = true;
          this.draggedNode = hit;
          this.dragOffset = { x: hit.x - worldPos.x, y: hit.y - worldPos.y };
          this.nodeDragStartPos = { x: hit.x, y: hit.y };
          this.hasDraggedNodeMoved = false;
          this.activeNode = hit;
          this.hoveredNode = hit;
          this.dragHistory = [{ x: hit.x, y: hit.y, time: performance.now() }];

          // Pin node in simulation
          if (this.worker) {
            this.worker.postMessage({ type: "drag_start", id: hit.id, x: hit.x, y: hit.y });
          } else if (this.fallbackEngine) {
            this.fallbackEngine.setNodePosition(hit.id, hit.x, hit.y, true);
            this.runFallbackLoop();
          }

          cvs.style.cursor = "grabbing";
          this.drawInteractive();

          if (this.options.onNodeDragStart) {
            this.options.onNodeDragStart(hit.data || hit);
          }
        } else {
          this.isPanning = true;
          this.dragStart = { x: sx, y: sy };
          this.hasPanned = false;
          cvs.style.cursor = "grabbing";
        }
      });

      const handlePointerUp = () => {
        if (this.isDraggingNode && this.draggedNode) {
          const targetNode = this.draggedNode;

          // Compute momentum release (fling) vector
          let vx = 0, vy = 0;
          const now = performance.now();
          const recent = this.dragHistory.filter(h => now - h.time <= 120);
          if (recent.length >= 2) {
            const first = recent[0];
            const last = recent[recent.length - 1];
            const dt = Math.max((last.time - first.time) / 1000, 0.016);
            vx = ((last.x - first.x) / dt) * 0.016;
            vy = ((last.y - first.y) / dt) * 0.016;
            const spd = Math.hypot(vx, vy);
            const maxFling = 24;
            if (spd > maxFling) {
              vx = (vx / spd) * maxFling;
              vy = (vy / spd) * maxFling;
            }
          }

          // Unpin and fling node in simulation
          if (this.worker) {
            this.worker.postMessage({ type: "drag_end", id: targetNode.id, vx, vy });
          } else if (this.fallbackEngine) {
            this.fallbackEngine.unpinNode(targetNode.id, vx, vy);
            this.runFallbackLoop();
          }

          if (this.hasDraggedNodeMoved) {
            this.savedCoordinates.set(targetNode.id, { x: targetNode.x, y: targetNode.y });
            this.rebuildQuadtree();
            this.justFinishedDrag = true;
            setTimeout(() => { this.justFinishedDrag = false; }, 80);
            if (this.options.onNodeDragEnd) {
              this.options.onNodeDragEnd(targetNode.data || targetNode);
            }
          }

          this.isDraggingNode = false;
          this.draggedNode = null;
        }

        if (this.isPanning) {
          if (this.hasPanned) {
            this.justFinishedDrag = true;
            setTimeout(() => { this.justFinishedDrag = false; }, 80);
          }
          this.isPanning = false;
        }

        cvs.style.cursor = this.hoveredNode ? "grab" : "default";
        this.drawBackground();
        this.drawInteractive();
      };

      window.addEventListener("mouseup", handlePointerUp);

      cvs.addEventListener("click", (e) => {
        if (this.justFinishedDrag) {
          this.justFinishedDrag = false;
          return;
        }
        if (this.nodes.length === 0) {
          if (this.options.onEmptyCanvasClick) {
            this.options.onEmptyCanvasClick();
          }
          return;
        }
        const rect = cvs.getBoundingClientRect();
        const sx = e.clientX - rect.left;
        const sy = e.clientY - rect.top;

        const hit = this.findNodeAt(sx, sy);
        if (hit) {
          this.activeNode = hit;
          this.hoveredNode = hit;
          this.drawInteractive();
          if (this.options.onNodeClick) {
            this.options.onNodeClick(hit.data || hit);
          }
        } else {
          this.activeNode = null;
          this.hoveredNode = null;
          this.drawInteractive();
        }
      });

      // Touch events for touchscreens / mobile
      cvs.addEventListener("touchstart", (e) => {
        if (e.touches.length === 1) {
          const touch = e.touches[0];
          const rect = cvs.getBoundingClientRect();
          const sx = touch.clientX - rect.left;
          const sy = touch.clientY - rect.top;

          const hit = this.findNodeAt(sx, sy);
          if (hit) {
            const worldPos = this.screenToWorld(sx, sy);
            this.isDraggingNode = true;
            this.draggedNode = hit;
            this.dragOffset = { x: hit.x - worldPos.x, y: hit.y - worldPos.y };
            this.nodeDragStartPos = { x: hit.x, y: hit.y };
            this.hasDraggedNodeMoved = false;
            this.activeNode = hit;
            this.hoveredNode = hit;
            this.dragHistory = [{ x: hit.x, y: hit.y, time: performance.now() }];

            if (this.worker) {
              this.worker.postMessage({ type: "drag_start", id: hit.id, x: hit.x, y: hit.y });
            } else if (this.fallbackEngine) {
              this.fallbackEngine.setNodePosition(hit.id, hit.x, hit.y, true);
              this.runFallbackLoop();
            }

            this.drawInteractive();
            if (this.options.onNodeDragStart) {
              this.options.onNodeDragStart(hit.data || hit);
            }
          } else {
            this.isPanning = true;
            this.dragStart = { x: sx, y: sy };
            this.hasPanned = false;
          }
        }
      }, { passive: true });

      cvs.addEventListener("touchmove", (e) => {
        if (e.touches.length === 1) {
          const touch = e.touches[0];
          const rect = cvs.getBoundingClientRect();
          const sx = touch.clientX - rect.left;
          const sy = touch.clientY - rect.top;

          if (this.isDraggingNode && this.draggedNode) {
            const worldPos = this.screenToWorld(sx, sy);
            const newX = worldPos.x + this.dragOffset.x;
            const newY = worldPos.y + this.dragOffset.y;

            if (Math.hypot(newX - this.nodeDragStartPos.x, newY - this.nodeDragStartPos.y) > 2) {
              this.hasDraggedNodeMoved = true;
            }

            this.draggedNode.x = newX;
            this.draggedNode.y = newY;
            if (this.draggedNode.data && typeof this.draggedNode.data === "object") {
              this.draggedNode.data.position = { x: newX, y: newY };
            }

            this.dragHistory.push({ x: newX, y: newY, time: performance.now() });
            if (this.dragHistory.length > 5) this.dragHistory.shift();

            if (this.worker) {
              this.worker.postMessage({ type: "drag_move", id: this.draggedNode.id, x: newX, y: newY });
            } else if (this.fallbackEngine) {
              this.fallbackEngine.setNodePosition(this.draggedNode.id, newX, newY, true);
              this.runFallbackLoop();
            }

            this.drawBackground();
            this.drawInteractive();

            if (this.options.onNodeDrag) {
              this.options.onNodeDrag(this.draggedNode.data || this.draggedNode, newX, newY);
            }
          } else if (this.isPanning) {
            const dx = sx - this.dragStart.x;
            const dy = sy - this.dragStart.y;
            if (Math.hypot(dx, dy) > 2) {
              this.hasPanned = true;
            }
            this.transform.panX += dx;
            this.transform.panY += dy;
            this.dragStart.x = sx;
            this.dragStart.y = sy;
            this.drawBackground();
            this.drawInteractive();
          }
        }
      }, { passive: true });

      cvs.addEventListener("touchend", () => {
        handlePointerUp();
      });

      // Smooth Wheel Zoom around cursor
      cvs.addEventListener("wheel", (e) => {
        e.preventDefault();
        const rect = cvs.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const zoomFactor = e.deltaY < 0 ? 1.14 : 0.88;
        const world = this.screenToWorld(mouseX, mouseY);

        const newScale = Math.max(
          this.options.minScale,
          Math.min(this.options.maxScale, this.transform.scale * zoomFactor)
        );

        this.transform.scale = newScale;
        this.transform.panX = mouseX - world.x * newScale;
        this.transform.panY = mouseY - world.y * newScale;

        this.drawBackground();
        this.drawInteractive();
      }, { passive: false });

      cvs.addEventListener("mouseleave", () => {
        if (!this.isDraggingNode && !this.isPanning) {
          if (this.hoveredNode) {
            this.hoveredNode = null;
            this.drawInteractive();
          }
        }
      });

      if (window.ResizeObserver) {
        this.resizeObserver = new ResizeObserver((entries) => {
          for (const entry of entries) {
            const newWidth = Math.floor(entry.contentRect.width);
            const newHeight = Math.floor(entry.contentRect.height);
            if (newWidth > 50 && newHeight > 50) {
              if (Math.abs(this.width - newWidth) > 2 || Math.abs(this.height - newHeight) > 2) {
                this.resize(newWidth, newHeight, false);
              }
            }
          }
        });
        this.resizeObserver.observe(this.container);
      }
    }

    /**
     * Explorer Mode Hover Update:
     * Strictly performs Quadtree hit-testing for hover highlights only.
     * Lights up target node in cyan (#38bdf8), highlights 1-hop connected edges, displays proximity label.
     * NEVER triggers physics repulsion or relayout.
     */
    updateHoveredNode(clientX, clientY) {
      if (!this.interactiveCanvas || !this.quadtree || this.nodes.length === 0) return null;
      const rect = this.interactiveCanvas.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return null;

      const sx = clientX - rect.left;
      const sy = clientY - rect.top;

      if (sx < 0 || sy < 0 || sx > rect.width || sy > rect.height) {
        if (this.hoveredNode) {
          this.hoveredNode = null;
          this.drawInteractive();
          if (this.options.onNodeHover) {
            this.options.onNodeHover(null);
          }
        }
        if (this.interactiveCanvas) {
          this.interactiveCanvas.style.cursor = "default";
        }
        return null;
      }

      const hit = this.findNodeAt(sx, sy);
      this.interactiveCanvas.style.cursor = hit ? "grab" : "default";

      if (hit !== this.hoveredNode) {
        this.hoveredNode = hit;
        this.drawInteractive();
        if (this.options.onNodeHover) {
          this.options.onNodeHover(hit ? (hit.data || hit) : null);
        }
      }
      return hit;
    }

    clearHover() {
      if (this.hoveredNode) {
        this.hoveredNode = null;
        this.drawInteractive();
        if (this.options.onNodeHover) {
          this.options.onNodeHover(null);
        }
      }
      if (this.interactiveCanvas) {
        this.interactiveCanvas.style.cursor = "default";
      }
    }

    focusNode(id) {
      const node = this.nodeMap.get(id);
      if (!node) return;

      this.activeNode = node;
      this.hoveredNode = node;

      const targetScale = Math.max(this.transform.scale, 1.2);
      this.transform.scale = targetScale;
      this.transform.panX = this.width / 2 - node.x * targetScale;
      this.transform.panY = this.height / 2 - node.y * targetScale;

      this.drawBackground();
      this.drawInteractive();
    }

    highlightNodes(ids) {
      if (!ids || !ids.length) return;
      const validNodes = ids.map(id => this.nodeMap.get(id)).filter(Boolean);
      if (!validNodes.length) return;

      this.activeNode = validNodes[0];
      this.hoveredNode = validNodes[0];
      this.highlightedNodeIds = new Set(validNodes.map(n => n.id));

      if (validNodes.length === 1) {
        return this.focusNode(validNodes[0].id);
      }

      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (let i = 0; i < validNodes.length; i++) {
        const n = validNodes[i];
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      }

      const cx = (minX + maxX) / 2;
      const cy = (minY + maxY) / 2;
      const spanX = Math.max(maxX - minX + 160, 200);
      const spanY = Math.max(maxY - minY + 160, 200);
      const fitScale = Math.min(this.width / spanX, this.height / spanY, 1.5);
      const targetScale = Math.max(this.options.minScale, Math.min(this.options.maxScale, fitScale));

      this.transform.scale = targetScale;
      this.transform.panX = this.width / 2 - cx * targetScale;
      this.transform.panY = this.height / 2 - cy * targetScale;

      this.drawBackground();
      this.drawInteractive();
    }

    zoomIn() {
      const cx = this.width / 2;
      const cy = this.height / 2;
      const world = this.screenToWorld(cx, cy);
      this.transform.scale = Math.min(this.options.maxScale, this.transform.scale * 1.25);
      this.transform.panX = cx - world.x * this.transform.scale;
      this.transform.panY = cy - world.y * this.transform.scale;
      this.drawBackground();
      this.drawInteractive();
    }

    zoomOut() {
      const cx = this.width / 2;
      const cy = this.height / 2;
      const world = this.screenToWorld(cx, cy);
      this.transform.scale = Math.max(this.options.minScale, this.transform.scale / 1.25);
      this.transform.panX = cx - world.x * this.transform.scale;
      this.transform.panY = cy - world.y * this.transform.scale;
      this.drawBackground();
      this.drawInteractive();
    }

    recomputeLayout(scale) {
      if (this.nodes.length === 0) {
        this.fit();
        return;
      }
      const computedLayout = computeGalaxyLayout(
        this.nodes.map(n => ({ data: n.data, id: n.id, position: { x: n.x, y: n.y } })),
        this.edges.map(e => ({ data: e.data, id: e.id, source: e.source, target: e.target })),
        { scale: scale || Math.min(this.width, this.height) * 0.95 }
      );
      for (let i = 0; i < this.nodes.length; i++) {
        const n = this.nodes[i];
        if (computedLayout[n.id]) {
          n.x = computedLayout[n.id].x;
          n.y = computedLayout[n.id].y;
          if (n.data && typeof n.data === "object") {
            n.data.position = { x: n.x, y: n.y };
          }
        }
      }
      this.rebuildQuadtree();
      this.fit();

      // Wake simulation
      if (this.worker) {
        this.worker.postMessage({
          type: "init",
          nodes: this.nodes.map(n => ({ id: n.id, x: n.x, y: n.y, radius: n.radius, degree: n.degree })),
          edges: this.edges.map(e => ({ source: e.source, target: e.target, weight: e.weight }))
        });
      } else if (this.fallbackEngine) {
        this.fallbackEngine.init(this.nodes, this.edges);
        this.fallbackEngine.wake(1.0);
        this.runFallbackLoop();
      }
    }

    wakePhysics(alpha = 0.35) {
      if (this.worker) {
        this.worker.postMessage({ type: "wake", alpha });
      } else if (this.fallbackEngine) {
        this.fallbackEngine.wake(alpha);
        this.runFallbackLoop();
      }
    }

    initGlobalAmbientPointerTracking() {
      if (this._hasBoundGlobalPointer) return;
      this._hasBoundGlobalPointer = true;

      this._globalPointerMoveHandler = (e) => {
        if (!this.container || !this.interactiveCanvas) return;
        if (this.nodes.length === 0) return;

        const rect = this.interactiveCanvas.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        // Ensure mouse movement anywhere on screen translates into canvas space
        // taking active zoom (scale) and pan transforms into account
        const sx = e.clientX - rect.left;
        const sy = e.clientY - rect.top;
        const world = this.screenToWorld(sx, sy);

        this.ambientPointer = {
          active: true,
          clientX: e.clientX,
          clientY: e.clientY,
          screenX: sx,
          screenY: sy,
          worldX: world.x,
          worldY: world.y,
          lastTime: performance.now()
        };

        this.scheduleAmbientTick();
      };

      this._globalPointerLeaveHandler = () => {
        if (this.ambientPointer) {
          this.ambientPointer.active = false;
        }
      };

      window.addEventListener("pointermove", this._globalPointerMoveHandler, { passive: true });
      window.addEventListener("pointerleave", this._globalPointerLeaveHandler, { passive: true });
    }

    scheduleAmbientTick() {
      if (this.ambientRafPending) return;
      this.ambientRafPending = true;
      requestAnimationFrame(() => {
        this.ambientRafPending = false;
        this.processAmbientRepulsion();
      });
    }

    processAmbientRepulsion() {
      // Functional Graph Explorer Canvas (.split-graph / #app-workspace):
      // Strictly disable cursor repulsion: The mouse pointer must never push or scatter nodes simply by gliding across the canvas.
      const isHeroActive = (typeof document !== "undefined") && (
        document.body.classList.contains("hero-active") ||
        Boolean(document.querySelector("#app")?.classList.contains("hero-active"))
      );
      if (!isHeroActive) {
        if (this.ambientPointer) this.ambientPointer.active = false;
        return;
      }

      if (!this.ambientPointer || !this.ambientPointer.active) return;
      if (this.nodes.length === 0) return;

      const scale = this.transform.scale || 1.0;
      // Ambient Repulsion Field: R_field ≈ 100px - 140px in screen space
      const screenRadius = 125;
      const worldRadius = screenRadius / scale;
      const wx = this.ambientPointer.worldX;
      const wy = this.ambientPointer.worldY;
      const kMouse = 28000;

      // Zero-lag optimization: filter candidate nodes within R_field using 2D Quadtree spatial index
      const candidates = this.quadtree ? this.quadtree.queryRadius(wx, wy, worldRadius) : [];
      if (candidates.length === 0) return;

      if (this.worker) {
        this.worker.postMessage({
          type: "ambient_repel",
          x: wx,
          y: wy,
          radius: worldRadius,
          kMouse: kMouse,
          alpha: 0.08
        });
        this.isPhysicsRunning = true;
      } else if (this.fallbackEngine) {
        this.fallbackEngine.applyAmbientRepulsion(wx, wy, worldRadius, kMouse, 0.08);
        this.isPhysicsRunning = true;
        this.runFallbackLoop();
      }
    }

    destroy() {
      if (this._globalPointerMoveHandler) {
        window.removeEventListener("pointermove", this._globalPointerMoveHandler);
        window.removeEventListener("pointerleave", this._globalPointerLeaveHandler);
      }
      if (this.resizeObserver) {
        this.resizeObserver.disconnect();
      }
      if (this.worker) {
        this.worker.terminate();
        this.worker = null;
      }
      if (this.fallbackRaf) {
        cancelAnimationFrame(this.fallbackRaf);
      }
      this.bgCanvas.remove();
      this.interactiveCanvas.remove();
    }
  }

  // Export layout functions, color utilities, and engine class
  ObsidianGalaxyEngine.computeGalaxyLayout = computeGalaxyLayout;
  ObsidianGalaxyEngine.GalaxyQuadtree = GalaxyQuadtree;
  ObsidianGalaxyEngine.PhysicsEngine = PhysicsEngine;
  ObsidianGalaxyEngine.BHNode = BHNode;
  ObsidianGalaxyEngine.DEFAULT_SEMANTIC_PALETTE = DEFAULT_SEMANTIC_PALETTE;
  ObsidianGalaxyEngine.NEUTRAL_LEAF_COLOR = NEUTRAL_LEAF_COLOR;
  ObsidianGalaxyEngine.compileNodeColors = compileNodeColors;

  return ObsidianGalaxyEngine;
});
