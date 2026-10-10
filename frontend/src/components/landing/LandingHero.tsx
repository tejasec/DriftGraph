import React from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { useNotesStore } from '@/stores/useNotesStore';
import {
  ArrowRight,
  GitFork,
  Boxes,
  Mic,
  FileScan,
  Database,
  Moon,
  Sun,
  Sparkles,
} from 'lucide-react';

export const LandingHero: React.FC = () => {
  const { setCurrentScreen, theme, toggleTheme } = useUIStore();
  const { createNote } = useNotesStore();

  const handleExploreSample = async () => {
    try {
      await createNote(
        'Welcome to DriftGraph',
        '# Welcome to DriftGraph\n\nDriftGraph is a local-first semantic knowledge graph platform with Sentence-BERT embeddings.\n\nConnect your thoughts freely.'
      );
    } catch {
      // Proceed even if note already exists
    }
    setCurrentScreen('workspace');
  };

  return (
    <div
      id="hero-landing"
      className="relative min-h-screen w-full flex flex-col justify-between p-6 sm:p-12 overflow-y-auto bg-[#080B12] text-[#E9ECF6]"
    >
      {/* Top Navbar */}
      <header className="flex items-center justify-between z-10 w-full max-w-6xl mx-auto">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#2FD9C4] to-[#A98CFB] flex items-center justify-center text-[#080B12] font-bold shadow-md shadow-[#2FD9C4]/20">
            DG
          </div>
          <span className="font-display font-semibold text-lg tracking-tight">Drift Graph</span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl bg-[#111726] border border-[#212B41] text-[#9AA3BC] hover:text-[#E9ECF6] transition-all"
            title="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button
            id="enterWorkspaceBtnTop"
            onClick={() => setCurrentScreen('workspace')}
            className="px-4 py-2 rounded-xl bg-[#111726] hover:bg-[#151C2E] text-xs font-semibold border border-[#212B41] text-[#E9ECF6] transition-all flex items-center gap-2"
          >
            <span>Launch Workspace</span>
            <ArrowRight className="w-3.5 h-3.5 text-[#2FD9C4]" />
          </button>
        </div>
      </header>

      {/* Hero Center Content */}
      <main className="flex flex-col items-center text-center my-auto py-12 z-10 max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#111726] border border-[#212B41] text-[#2FD9C4] text-xs font-mono font-medium mb-8 shadow-inner">
          <Sparkles className="w-3.5 h-3.5" />
          <span>LOCAL-FIRST · PRIVACY-FOCUSED · 60 FPS GRAPH RAG</span>
        </div>

        <h1 className="font-display text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight text-[#E9ECF6] mb-6 leading-[1.08]">
          Notes in. <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#2FD9C4] via-[#A98CFB] to-[#FB7BA6]">
            Knowledge Galaxy out.
          </span>
        </h1>

        <p className="text-sm sm:text-lg text-[#9AA3BC] max-w-2xl mb-10 leading-relaxed font-body">
          Transform unorganized Markdown notes into a real-time, interactive 2D semantic knowledge galaxy.
          Zero cloud dependencies, on-device vector embeddings, and multi-modal intelligence.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4">
          <button
            id="enterWorkspaceBtn"
            onClick={() => setCurrentScreen('workspace')}
            className="px-7 py-3.5 rounded-xl bg-[#2FD9C4] hover:bg-[#2FD9C4]/90 text-[#080B12] font-semibold text-sm transition-all shadow-lg shadow-[#2FD9C4]/25 flex items-center gap-2.5 transform hover:-translate-y-0.5"
          >
            <span id="btn-open-explorer">Enter Workspace</span>
            <ArrowRight className="w-4 h-4" />
          </button>
          <button
            id="exploreVaultBtn"
            onClick={handleExploreSample}
            className="px-6 py-3.5 rounded-xl bg-[#111726] hover:bg-[#151C2E] text-[#E9ECF6] font-medium text-sm border border-[#212B41] transition-all flex items-center gap-2"
          >
            <Database className="w-4 h-4 text-[#A98CFB]" />
            <span>Open Research Vault</span>
          </button>
        </div>
      </main>

      {/* Feature Grid */}
      <footer className="w-full max-w-6xl mx-auto z-10 pt-8 pb-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-[#111726]/60 border border-[#212B41] backdrop-blur-sm hover:border-[#2FD9C4]/50 transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#2FD9C4]/10 text-[#2FD9C4] flex items-center justify-center mb-3">
              <GitFork className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-[#E9ECF6] mb-1">Auto-linking</h3>
            <p className="text-xs text-[#9AA3BC] leading-relaxed">
              384-dimensional Sentence-BERT embeddings connect notes as meaning overlaps.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-[#111726]/60 border border-[#212B41] backdrop-blur-sm hover:border-[#A98CFB]/50 transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#A98CFB]/10 text-[#A98CFB] flex items-center justify-center mb-3">
              <Boxes className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-[#E9ECF6] mb-1">Leiden Clustering</h3>
            <p className="text-xs text-[#9AA3BC] leading-relaxed">
              Automatic community detection partitions notes into color-coded thematic galaxies.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-[#111726]/60 border border-[#212B41] backdrop-blur-sm hover:border-[#FB7BA6]/50 transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#FB7BA6]/10 text-[#FB7BA6] flex items-center justify-center mb-3">
              <Mic className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-[#E9ECF6] mb-1">Voice RAG</h3>
            <p className="text-xs text-[#9AA3BC] leading-relaxed">
              Ask audible queries and get synthesized answers with highlighted canvas nodes.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-[#111726]/60 border border-[#212B41] backdrop-blur-sm hover:border-[#F2B84B]/50 transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#F2B84B]/10 text-[#F2B84B] flex items-center justify-center mb-3">
              <FileScan className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-[#E9ECF6] mb-1">Document OCR</h3>
            <p className="text-xs text-[#9AA3BC] leading-relaxed">
              Scan multi-page PDFs and images with bounding box confidence inspection.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};
