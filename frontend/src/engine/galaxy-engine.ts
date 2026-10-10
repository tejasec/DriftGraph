import { GraphNode, GraphEdge, Community } from '@/types/graph';

export interface GalaxyEngineOptions {
  backgroundColor?: string;
  useWorker?: boolean;
  onNodeClick?: (nodeId: string, nodeData: any) => void;
  onNodeHover?: (nodeId: string | null, nodeData: any) => void;
  onBgClick?: () => void;
  [key: string]: any;
}

export class GalaxyEngineAdapter {
  private instance: any = null;
  private container: HTMLElement;
  private options: GalaxyEngineOptions;
  private resizeObserver: ResizeObserver | null = null;
  private isDestroyed = false;

  constructor(container: HTMLElement, options: GalaxyEngineOptions = {}) {
    this.container = container;
    this.options = options;
    this.init();
  }

  private async init() {
    // Ensure ObsidianGalaxyEngine is loaded on window
    const EngineClass = (window as any).ObsidianGalaxyEngine;
    if (EngineClass) {
      this.instantiateEngine(EngineClass);
    } else {
      // Dynamically load script if not already on window
      try {
        await this.loadScript('/static/assets/js/galaxy-engine.js');
        const LoadedEngine = (window as any).ObsidianGalaxyEngine;
        if (LoadedEngine && !this.isDestroyed) {
          this.instantiateEngine(LoadedEngine);
        }
      } catch (err) {
        console.error('Failed to load galaxy-engine.js:', err);
      }
    }
  }

  private loadScript(src: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing) {
        existing.addEventListener('load', () => resolve());
        existing.addEventListener('error', (e) => reject(e));
        if ((existing as any).loaded) {
          resolve();
          return;
        }
      }
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.onload = () => {
        (script as any).loaded = true;
        resolve();
      };
      script.onerror = (e) => reject(e);
      document.head.appendChild(script);
    });
  }

  private instantiateEngine(EngineClass: any) {
    if (this.isDestroyed) return;

    this.instance = new EngineClass(this.container, {
      backgroundColor: this.options.backgroundColor || '#080B12',
      useWorker: this.options.useWorker ?? true,
      onNodeClick: (node: any) => {
        if (this.options.onNodeClick) {
          const id = node.id || (node.data && node.data.id);
          this.options.onNodeClick(id, node);
        }
      },
      onNodeHover: (node: any) => {
        if (this.options.onNodeHover) {
          const id = node ? (node.id || (node.data && node.data.id)) : null;
          this.options.onNodeHover(id, node);
        }
      },
      onBgClick: () => {
        if (this.options.onBgClick) {
          this.options.onBgClick();
        }
      },
    });

    (window as any).galaxyEngine = this.instance;

    // Self-healing ResizeObserver
    this.resizeObserver = new ResizeObserver(() => {
      if (this.instance && typeof this.instance.resize === 'function') {
        this.instance.resize();
      }
    });
    this.resizeObserver.observe(this.container);
  }

  public loadData(nodes: GraphNode[], edges: GraphEdge[], communities: Community[] = []) {
    if (this.instance && typeof this.instance.loadData === 'function') {
      this.instance.loadData({
        nodes,
        edges,
        communities,
      });
    } else {
      // Retry in 100ms if engine still initializing
      setTimeout(() => {
        if (this.instance && typeof this.instance.loadData === 'function') {
          this.instance.loadData({ nodes, edges, communities });
        }
      }, 150);
    }
  }

  public resize() {
    if (this.instance && typeof this.instance.resize === 'function') {
      this.instance.resize();
    }
  }

  public fit() {
    if (this.instance && typeof this.instance.fit === 'function') {
      this.instance.fit();
    }
  }

  public zoomIn() {
    if (this.instance && typeof this.instance.zoomIn === 'function') {
      this.instance.zoomIn();
    }
  }

  public zoomOut() {
    if (this.instance && typeof this.instance.zoomOut === 'function') {
      this.instance.zoomOut();
    }
  }

  public selectNode(id: string | null) {
    if (this.instance && typeof this.instance.selectNode === 'function') {
      this.instance.selectNode(id);
    }
  }

  public setHoveredNode(id: string | null) {
    if (this.instance && typeof this.instance.setHoveredNode === 'function') {
      this.instance.setHoveredNode(id);
    }
  }

  public destroy() {
    this.isDestroyed = true;
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
    if (this.instance && typeof this.instance.destroy === 'function') {
      this.instance.destroy();
      this.instance = null;
    }
    if ((window as any).galaxyEngine === this.instance) {
      delete (window as any).galaxyEngine;
    }
  }
}
