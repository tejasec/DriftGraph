import { create } from 'zustand';
import { GraphAnalyticsReport, PathResult } from '@/types/analytics';
import { analyticsApi } from '@/api/client';

interface AnalyticsState {
  report: GraphAnalyticsReport | null;
  pathResult: PathResult | null;
  pathSource: string;
  pathTarget: string;
  isFindingPath: boolean;
  isLoading: boolean;
  error: string | null;

  fetchReport: () => Promise<void>;
  findPath: (source: string, target: string) => Promise<void>;
  setPathSource: (s: string) => void;
  setPathTarget: (t: string) => void;
  clearPath: () => void;
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
  report: null,
  pathResult: null,
  pathSource: '',
  pathTarget: '',
  isFindingPath: false,
  isLoading: false,
  error: null,

  fetchReport: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await analyticsApi.getReport();
      set({ report: data, isLoading: false });
    } catch (err: any) {
      console.warn('Failed to fetch analytics report', err);
      set({ error: err.message || 'Failed to load report', isLoading: false });
    }
  },

  findPath: async (source: string, target: string) => {
    if (!source.trim() || !target.trim()) return;
    set({ isFindingPath: true, error: null });
    try {
      const res = await analyticsApi.findPath(source.trim(), target.trim());
      set({ pathResult: res, isFindingPath: false });
    } catch (err: any) {
      set({
        error: err.message || 'No direct path found between concepts',
        pathResult: {
          source,
          target,
          path_found: false,
          hops: 0,
          node_sequence: [],
          steps: [],
          narrative: `No connecting path found between "${source}" and "${target}".`,
        },
        isFindingPath: false,
      });
    }
  },

  setPathSource: (s) => set({ pathSource: s }),
  setPathTarget: (t) => set({ pathTarget: t }),
  clearPath: () => set({ pathResult: null, pathSource: '', pathTarget: '' }),
}));
