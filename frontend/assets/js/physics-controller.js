/**
 * DriftGraph Physics Controller
 * Scoped cursor physics controller for Hero View vs. Graph Explorer Canvas.
 * 
 * Interaction Scopes:
 * 1. Landing / Hero Screen Background (#hero-landing):
 *    - Ambient radial force field enabled (R_field ≈ 100px - 130px).
 *    - Pointer coordinates apply repulsion forces to background nodes,
 *      causing them to gently scatter and flex connected edges before springing back into place.
 * 
 * 2. Functional Graph Explorer Canvas (.split-graph / #app-workspace):
 *    - Strictly disable cursor repulsion: The mouse pointer must never push or scatter nodes simply by gliding across the canvas.
 *    - Nodes remain fixed in their settled positions unless explicitly interacted with.
 *    - Interaction is limited to:
 *      * Direct Hover: Lighting up target node in cyan, highlighting 1-hop connected edges, proximity label.
 *      * Direct Kinematic Drag: Moving a single node, surrounding nodes deflect only via hard elastic body collisions (Rc = r_node + 4px).
 *      * Pan / Zoom: Standard canvas navigation without triggering physics relayout.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.PhysicsController = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Determine whether the Landing / Hero screen is currently active.
   * Checks both document.body and #app container classes.
   * @returns {boolean}
   */
  function isHeroActive() {
    if (typeof document === 'undefined') return false;
    return (
      document.body.classList.contains('hero-active') ||
      Boolean(document.querySelector('#app')?.classList.contains('hero-active'))
    );
  }

  /**
   * Apply ambient radial force field to hero background nodes.
   * R_field ≈ 100px - 130px.
   * @param {number} clientX
   * @param {number} clientY
   */
  function applyAmbientRepulsion(clientX, clientY) {
    if (typeof window === 'undefined') return;

    // 1. Dispatch to driftCanvas pointer controller
    if (window._driftCanvasPointer && typeof window._driftCanvasPointer.update === 'function') {
      window._driftCanvasPointer.update(clientX, clientY);
      return;
    }

    // 2. Direct element property fallback
    const driftCanvasEl = typeof document !== 'undefined' ? document.getElementById('driftCanvas') : null;
    if (driftCanvasEl && driftCanvasEl.__driftPointer && typeof driftCanvasEl.__driftPointer.update === 'function') {
      driftCanvasEl.__driftPointer.update(clientX, clientY);
    }
  }

  /**
   * Explorer Mode Hover Update:
   * Strictly performs Quadtree hit-testing for hover highlights only.
   * NEVER applies repulsion or physics forces to nodes.
   * @param {number} clientX
   * @param {number} clientY
   * @returns {any} Hovered node or null
   */
  function updateHoveredNode(clientX, clientY) {
    if (typeof window === 'undefined') return null;

    if (window.galaxyEngine && typeof window.galaxyEngine.updateHoveredNode === 'function') {
      return window.galaxyEngine.updateHoveredNode(clientX, clientY);
    }
    return null;
  }

  /**
   * Scoped pointer move handler adhering to task specification.
   * @param {PointerEvent|MouseEvent} event
   */
  function handlePointerMove(event) {
    const isHero = isHeroActive();

    if (isHero) {
      // Apply ambient repulsion vector to nearby nodes
      applyAmbientRepulsion(event.clientX, event.clientY);
    } else {
      // In explorer mode: Only perform Quadtree hit-testing for hover highlights
      updateHoveredNode(event.clientX, event.clientY);
    }
  }

  /**
   * Pointer leave handler to cleanly deactivate hover states and ambient fields.
   */
  function handlePointerLeave() {
    if (typeof window === 'undefined') return;

    if (window._driftCanvasPointer && typeof window._driftCanvasPointer.deactivate === 'function') {
      window._driftCanvasPointer.deactivate();
    }
    if (window.galaxyEngine && typeof window.galaxyEngine.clearHover === 'function') {
      window.galaxyEngine.clearHover();
    }
  }

  /**
   * Bind global pointer events.
   */
  function init() {
    if (typeof window !== 'undefined') {
      window.addEventListener('pointermove', handlePointerMove, { passive: true });
      window.addEventListener('pointerleave', handlePointerLeave, { passive: true });
    }
  }

  // Auto-bind in browser if DOM is ready or on load
  if (typeof window !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  }

  return {
    handlePointerMove,
    applyAmbientRepulsion,
    updateHoveredNode,
    handlePointerLeave,
    isHeroActive,
    init
  };
});
