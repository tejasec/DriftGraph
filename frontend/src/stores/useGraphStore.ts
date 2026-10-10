import { create } from 'zustand';
import { GraphNode, GraphEdge, Community } from '@/types/graph';
import { graphApi } from '@/api/client';

interface GraphState {
  nodes: GraphNode[];
  edges: GraphEdge[];
  communities: Community[];
  selectedNodeId: string | null;
  hoveredNodeId: string | null;
  activeCommunityLevel: number;
  similarityThreshold: number;
  coulombRepulsion: number;
  springTension: number;
  layoutMode: 'galaxy' | 'network';
  isLoading: boolean;
  error: string | null;

  fetchGraph: (threshold?: number) => Promise<void>;
  fetchCommunities: (level?: number) => Promise<void>;
  recomputeLayout: (engine?: string) => Promise<void>;
  setSelectedNodeId: (id: string | null) => void;
  setHoveredNodeId: (id: string | null) => void;
  setActiveCommunityLevel: (level: number) => void;
  setSimilarityThreshold: (val: number) => void;
  setCoulombRepulsion: (val: number) => void;
  setSpringTension: (val: number) => void;
  setLayoutMode: (mode: 'galaxy' | 'network') => void;
}

export const useGraphStore = create<GraphState>((set, get) => ({
  nodes: [],
  edges: [],
  communities: [],
  selectedNodeId: null,
  hoveredNodeId: null,
  activeCommunityLevel: 1,
  similarityThreshold: 0.75,
  coulombRepulsion: 5200,
  springTension: 0.045,
  layoutMode: 'galaxy',
  isLoading: false,
  error: null,

  fetchGraph: async (threshold?: number) => {
    set({ isLoading: true, error: null });
    try {
      const thresh = threshold !== undefined ? threshold : get().similarityThreshold;
      const data = await graphApi.getElements(thresh);
      set({ nodes: data.nodes || [], edges: data.edges || [], isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch graph data', isLoading: false });
    }
  },

  fetchCommunities: async (level?: number) => {
    try {
      const comms = await graphApi.getCommunities(level);
      set({ communities: comms || [] });
    } catch (err: any) {
      console.warn('Failed to fetch communities', err);
    }
  },

  recomputeLayout: async (engine = 'galaxy') => {
    set({ isLoading: true });
    try {
      const data = await graphApi.computeLayout(engine, 500, true);
      set({ nodes: data.nodes || [], edges: data.edges || [], isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to recompute layout', isLoading: false });
    }
  },

  setSelectedNodeId: (id: string | null) => set({ selectedNodeId: id }),
  setHoveredNodeId: (id: string | null) => set({ hoveredNodeId: id }),
  setActiveCommunityLevel: (level: number) => set({ activeCommunityLevel: level }),
  setSimilarityThreshold: (val: number) => set({ similarityThreshold: val }),
  setCoulombRepulsion: (val: number) => set({ coulombRepulsion: val }),
  setSpringTension: (val: number) => set({ springTension: val }),
  setLayoutMode: (mode: 'galaxy' | 'network') => set({ layoutMode: mode }),
}));
