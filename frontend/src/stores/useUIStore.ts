import { create } from 'zustand';
import { statusApi } from '@/api/client';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  citations?: any[];
  latency?: number;
}

interface UIState {
  currentScreen: 'landing' | 'workspace';
  theme: 'dark' | 'light';
  activeModal: string | null;
  deleteModalTarget: { noteIds: string[]; title?: string; isPermanent?: boolean } | null;
  communityReportData: { title?: string; summary?: string; entities?: string[] } | null;
  isDemoMode: boolean;
  apiProvider: string;
  splitRatio: number;
  ragMode: 'auto' | 'global' | 'local';
  chatMessages: ChatMessage[];

  setCurrentScreen: (screen: 'landing' | 'workspace') => void;
  setTheme: (theme: 'dark' | 'light') => void;
  toggleTheme: () => void;
  openModal: (modal: string) => void;
  closeModal: () => void;
  openDeleteModal: (target: { noteIds: string[]; title?: string; isPermanent?: boolean }) => void;
  openCommunityReport: (data: { title?: string; summary?: string; entities?: string[] }) => void;
  setSplitRatio: (ratio: number) => void;
  setRagMode: (mode: 'auto' | 'global' | 'local') => void;
  addChatMessage: (msg: ChatMessage) => void;
  clearChat: () => void;
  checkDiagnostics: () => Promise<void>;
}

export const useUIStore = create<UIState>((set, get) => ({
  currentScreen: 'landing',
  theme: 'dark',
  activeModal: null,
  deleteModalTarget: null,
  communityReportData: null,
  isDemoMode: false,
  apiProvider: 'local',
  splitRatio: 38,
  ragMode: 'auto',
  chatMessages: [],

  setCurrentScreen: (screen) => set({ currentScreen: screen }),

  setTheme: (theme) => {
    set({ theme });
    if (typeof document !== 'undefined') {
      if (theme === 'light') {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
        document.documentElement.setAttribute('data-theme', 'light');
      } else {
        document.documentElement.classList.remove('light');
        document.documentElement.classList.add('dark');
        document.documentElement.setAttribute('data-theme', 'dark');
      }
    }
  },

  toggleTheme: () => {
    const next = get().theme === 'dark' ? 'light' : 'dark';
    get().setTheme(next);
  },

  openModal: (modal) => set({ activeModal: modal }),
  closeModal: () => set({ activeModal: null, deleteModalTarget: null, communityReportData: null }),

  openDeleteModal: (target) => set({ activeModal: 'deleteConfirm', deleteModalTarget: target }),
  openCommunityReport: (data) => set({ activeModal: 'communityReport', communityReportData: data }),

  setSplitRatio: (ratio) => set({ splitRatio: Math.min(80, Math.max(20, ratio)) }),
  setRagMode: (mode) => set({ ragMode: mode }),

  addChatMessage: (msg) => set((s) => ({ chatMessages: [...s.chatMessages, msg] })),
  clearChat: () => set({ chatMessages: [] }),

  checkDiagnostics: async () => {
    try {
      const diag = await statusApi.diagnostics();
      if (diag && diag.demo_mode) {
        set({ isDemoMode: true, apiProvider: diag.llm_provider || 'hosted_api' });
      }
    } catch {
      // Diagnostics endpoint optional fallback
    }
  },
}));
