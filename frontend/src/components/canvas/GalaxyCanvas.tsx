import React, { useEffect, useRef } from 'react';
import { useGraphStore } from '@/stores/useGraphStore';
import { useNotesStore } from '@/stores/useNotesStore';
import { GalaxyEngineAdapter } from '@/engine/galaxy-engine';
import { ZoomIn, ZoomOut, Maximize2, Sparkles, Network } from 'lucide-react';

export const GalaxyCanvas: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const adapterRef = useRef<GalaxyEngineAdapter | null>(null);

  const {
    nodes,
    edges,
    communities,
    layoutMode,
    setLayoutMode,
    setSelectedNodeId,
    setHoveredNodeId,
    recomputeLayout,
  } = useGraphStore();

  const { selectNote, createNote } = useNotesStore();

  useEffect(() => {
    if (!containerRef.current) return;

    const adapter = new GalaxyEngineAdapter(containerRef.current, {
      backgroundColor: '#080B12',
      useWorker: true,
      onNodeClick: (nodeId) => {
        setSelectedNodeId(nodeId);
        if (nodeId) {
          selectNote(nodeId);
        }
      },
      onNodeHover: (nodeId) => {
        setHoveredNodeId(nodeId);
      },
      onBgClick: () => {
        setSelectedNodeId(null);
      },
    });

    adapterRef.current = adapter;

    return () => {
      adapter.destroy();
      adapterRef.current = null;
    };
  }, [setSelectedNodeId, setHoveredNodeId, selectNote]);

  // Sync data updates to canvas engine
  useEffect(() => {
    if (adapterRef.current && nodes) {
      adapterRef.current.loadData(nodes, edges, communities);
    }
  }, [nodes, edges, communities]);

  const handleZoomIn = () => adapterRef.current?.zoomIn();
  const handleZoomOut = () => adapterRef.current?.zoomOut();
  const handleFit = () => adapterRef.current?.fit();

  const handleSeedVault = async () => {
    try {
      await createNote(
        'Welcome to DriftGraph',
        '# Welcome to DriftGraph\n\nDriftGraph is a local-first semantic knowledge graph platform with 384-dimensional Sentence-BERT embeddings and Leiden community clustering.\n\nConnect concepts effortlessly.'
      );
      await createNote(
        'Knowledge Graphs and Embeddings',
        '# Knowledge Graphs and Embeddings\n\nHigh-dimensional embeddings allow computing cosine similarity between concepts, creating automated links without manual tagging.'
      );
    } catch (err) {
      console.error('Failed to seed sample vault', err);
    }
  };

  return (
    <div className="relative w-full h-full flex flex-col bg-[#080B12] overflow-hidden select-none">
      {/* Top Bar with Legend and Layout Controls */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1A2233] bg-[#0C111C]/80 backdrop-blur-md z-10">
        <div id="graphLegend" className="flex items-center gap-2 overflow-x-auto text-xs text-[#9AA3BC]">
          <span className="font-semibold text-[#5D6683] text-[11px] uppercase tracking-wider">Clusters:</span>
          {communities.slice(0, 6).map((c, idx) => {
            const colors = ['#38bdf8', '#34d399', '#a855f7', '#fbbf24', '#f43f5e', '#94a3b8'];
            const color = colors[idx % colors.length];
            return (
              <span
                key={c.id || idx}
                className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] bg-[#111726] border border-[#212B41]"
              >
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                <span>{c.name || `Cluster ${c.id}`}</span>
              </span>
            );
          })}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="flex items-center bg-[#111726] p-0.5 rounded-lg border border-[#212B41]">
            <button
              onClick={() => setLayoutMode('galaxy')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
                layoutMode === 'galaxy'
                  ? 'bg-[#2FD9C4]/15 text-[#2FD9C4] shadow-sm'
                  : 'text-[#9AA3BC] hover:text-[#E9ECF6]'
              }`}
              title="Obsidian-Style Galaxy Canvas Renderer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Galaxy</span>
            </button>
            <button
              onClick={() => setLayoutMode('network')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
                layoutMode === 'network'
                  ? 'bg-[#2FD9C4]/15 text-[#2FD9C4] shadow-sm'
                  : 'text-[#9AA3BC] hover:text-[#E9ECF6]'
              }`}
              title="Topological Network View"
            >
              <Network className="w-3.5 h-3.5" />
              <span>Network</span>
            </button>
          </div>

          <button
            onClick={() => recomputeLayout('galaxy')}
            className="px-2.5 py-1 text-xs font-medium rounded-md bg-[#111726] hover:bg-[#151C2E] text-[#9AA3BC] hover:text-[#E9ECF6] border border-[#212B41] transition-all"
            title="Recompute Sunflower Phyllotaxis Galaxy Layout"
          >
            Galaxy Layout
          </button>
          <button
            onClick={() => recomputeLayout('forceatlas2')}
            className="px-2.5 py-1 text-xs font-medium rounded-md bg-[#111726] hover:bg-[#151C2E] text-[#9AA3BC] hover:text-[#E9ECF6] border border-[#212B41] transition-all"
            title="Recompute Server-Side ForceAtlas2 Layout"
          >
            FA2 Layout
          </button>
        </div>
      </div>

      {/* Main Graph Canvas Viewport */}
      <div className="graph-canvas-wrap relative flex-1 w-full min-h-[400px]">
        <div
          id="galaxyGraphContainer"
          ref={containerRef}
          className="absolute inset-0 w-full h-full min-h-[400px] overflow-hidden"
        />

        {/* Viewport Floating Zoom Controls */}
        <div id="graphControls" className="absolute right-4 bottom-4 flex flex-col gap-1.5 z-20">
          <button
            id="gcZoomIn"
            onClick={handleZoomIn}
            className="w-8 h-8 rounded-lg bg-[#111726]/90 hover:bg-[#151C2E] text-[#E9ECF6] border border-[#212B41] shadow-lg flex items-center justify-center transition-all hover:scale-105"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            id="gcZoomOut"
            onClick={handleZoomOut}
            className="w-8 h-8 rounded-lg bg-[#111726]/90 hover:bg-[#151C2E] text-[#E9ECF6] border border-[#212B41] shadow-lg flex items-center justify-center transition-all hover:scale-105"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            id="gcFit"
            onClick={handleFit}
            className="w-8 h-8 rounded-lg bg-[#111726]/90 hover:bg-[#151C2E] text-[#E9ECF6] border border-[#212B41] shadow-lg flex items-center justify-center transition-all hover:scale-105"
            title="Fit to screen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>

        {/* Hint Pill */}
        <div
          id="graphHint"
          className="absolute left-4 bottom-4 px-2.5 py-1 rounded-full bg-[#111726]/80 border border-[#212B41] text-[#9AA3BC] text-[11px] font-mono pointer-events-none z-10"
        >
          tap a node to inspect · drag to orbit
        </div>

        {/* Empty State Overlay */}
        {nodes.length === 0 && (
          <div
            id="graphEmptyState"
            className="graph-empty-state absolute inset-0 flex items-center justify-center bg-[#080B12]/80 backdrop-blur-sm z-30"
          >
            <div className="empty-state-card max-w-sm p-6 rounded-2xl bg-[#111726] border border-[#212B41] shadow-2xl text-center flex flex-col items-center">
              <div className="w-12 h-12 rounded-full bg-[#2FD9C4]/10 text-[#2FD9C4] flex items-center justify-center mb-4">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="empty-state-title text-base font-semibold text-[#E9ECF6] mb-1">
                No notes in database
              </h3>
              <p className="empty-state-subtitle text-xs text-[#9AA3BC] mb-5 leading-relaxed">
                Create your first note or load the sample vault to explore your semantic knowledge graph.
              </p>
              <div className="empty-state-actions flex gap-2.5 w-full">
                <button
                  id="emptyCreateNoteBtn"
                  onClick={() => createNote('First Note', '# My First Note\n\nStart typing ideas here...')}
                  className="flex-1 py-2 px-3 rounded-lg bg-[#2FD9C4] hover:bg-[#2FD9C4]/90 text-[#080B12] font-semibold text-xs transition-all shadow-md"
                >
                  Create First Note
                </button>
                <button
                  id="emptySeedVaultBtn"
                  onClick={handleSeedVault}
                  className="flex-1 py-2 px-3 rounded-lg bg-[#151C2E] hover:bg-[#212B41] text-[#E9ECF6] font-medium text-xs border border-[#212B41] transition-all"
                >
                  Load Sample Vault
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
