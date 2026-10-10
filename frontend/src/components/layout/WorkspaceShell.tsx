import React, { useState, useEffect, useRef } from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { useGraphStore } from '@/stores/useGraphStore';
import { useNotesStore } from '@/stores/useNotesStore';
import { queryApi, statusApi } from '@/api/client';
import { NoteEditor } from '@/components/editor/NoteEditor';
import { GalaxyCanvas } from '@/components/canvas/GalaxyCanvas';
import { ToolsDrawer } from '@/components/tools/ToolsDrawer';
import { VoiceModal } from '@/components/modals/VoiceModal';
import { OCRStudioModal } from '@/components/modals/OCRStudioModal';
import { ClassifierModal } from '@/components/modals/ClassifierModal';
import { NotesGalleryModal } from '@/components/modals/NotesGalleryModal';
import { TemplateModal } from '@/components/modals/TemplateModal';
import { WebScraperModal } from '@/components/modals/WebScraperModal';
import { DeleteConfirmModal } from '@/components/modals/DeleteConfirmModal';
import { CommunityReportModal } from '@/components/modals/CommunityReportModal';
import {
  ArrowLeft,
  Sliders,
  Sun,
  Moon,
  Send,
  HelpCircle,
  AlertTriangle,
  ChevronRight,
  Boxes,
  Zap,
} from 'lucide-react';

export const WorkspaceShell: React.FC = () => {
  const {
    setCurrentScreen,
    theme,
    toggleTheme,
    openModal,
    isDemoMode,
    apiProvider,
    splitRatio,
    setSplitRatio,
    ragMode,
    setRagMode,
    chatMessages,
    addChatMessage,
    checkDiagnostics,
  } = useUIStore();

  const { fetchGraph, fetchCommunities, nodes, edges, communities } = useGraphStore();
  const { fetchNotes } = useNotesStore();

  const [askQuery, setAskQuery] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [showWhatItDoes, setShowWhatItDoes] = useState(false);
  const [apiStatus, setApiStatus] = useState('Online');
  const [isDraggingSplit, setIsDraggingSplit] = useState(false);

  const splitRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchGraph();
    fetchCommunities();
    fetchNotes();
    checkDiagnostics();
    statusApi
      .health()
      .then((h) => setApiStatus(`Online · ${h.app}`))
      .catch(() => setApiStatus('Offline'));
  }, [fetchGraph, fetchCommunities, fetchNotes, checkDiagnostics]);

  // Handle draggable split resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingSplit || !splitRef.current) return;
      const rect = splitRef.current.getBoundingClientRect();
      const newRatio = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitRatio(newRatio);
    };

    const handleMouseUp = () => {
      setIsDraggingSplit(false);
    };

    if (isDraggingSplit) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingSplit, setSplitRatio]);

  const handleAsk = async () => {
    const q = askQuery.trim();
    if (!q) return;

    addChatMessage({ role: 'user', text: q });
    setAskQuery('');
    setIsAsking(true);

    const startTime = performance.now();
    try {
      const res = await queryApi.ask({
        query: q,
        mode: ragMode,
      });
      const latency = Math.round(performance.now() - startTime);
      addChatMessage({
        role: 'assistant',
        text: res.answer,
        citations: res.citations,
        latency,
      });
    } catch (err: any) {
      addChatMessage({
        role: 'assistant',
        text: `Error: ${err.message || 'Failed to retrieve answer from knowledge graph'}`,
      });
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div
      id="app-workspace"
      className="relative w-screen h-screen flex flex-col bg-[#080B12] text-[#E9ECF6] overflow-hidden select-none"
    >
      {/* 1. Appbar Header */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-[#1A2233] bg-[#0C111C]/90 backdrop-blur-md z-30 shrink-0">
        <div className="flex items-center gap-3">
          <button
            id="backToLanding"
            onClick={() => setCurrentScreen('landing')}
            className="p-1.5 rounded-lg bg-[#151C2E] hover:bg-[#212B41] text-[#9AA3BC] hover:text-[#E9ECF6] transition-all"
            title="Back to landing"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="appbar-title font-display font-semibold text-sm tracking-tight">
            Drift Graph
          </div>
          <div className="status-pill inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#111726] border border-[#212B41] text-[11px] font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-[#2FD9C4] animate-pulse" />
            <span id="apiStatusLabel">{apiStatus}</span>
          </div>
        </div>

        {/* Center / Right Header Tools */}
        <div className="flex items-center gap-2">
          {/* What It Does Popover */}
          <div className="relative" id="whatItDoesWrapperApp">
            <button
              id="whatItDoesBtnApp"
              onClick={() => setShowWhatItDoes(!showWhatItDoes)}
              className="px-2.5 py-1 rounded-lg bg-[#111726] hover:bg-[#151C2E] border border-[#212B41] text-xs text-[#38BDF8] flex items-center gap-1.5 transition-all"
              title="Learn what DriftGraph does"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              <span>What it does</span>
            </button>

            {showWhatItDoes && (
              <div
                id="whatItDoesPopoverApp"
                className="absolute right-0 top-full mt-2 w-80 p-4 rounded-2xl bg-[#111726] border border-[#212B41] shadow-2xl z-50 text-xs space-y-2.5"
              >
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-[#38BDF8]">Local-First GraphRAG</span>
                  <button onClick={() => setShowWhatItDoes(false)} className="text-[#9AA3BC]">
                    ✕
                  </button>
                </div>
                <p className="text-[#9AA3BC] leading-relaxed">
                  Converts unorganized Markdown notes into a queryable semantic knowledge graph on your local
                  device using 384-dimensional Sentence-BERT vectors and Leiden communities.
                </p>
              </div>
            )}
          </div>

          {/* Tools & Metrics Drawer Button */}
          <div className="header-menu-wrapper" id="headerMenuWrapper">
            <button
              id="headerToolsBtn"
              onClick={() => openModal('toolsDrawer')}
              className="px-3 py-1 rounded-lg bg-[#111726] hover:bg-[#151C2E] border border-[#2FD9C4]/40 text-xs font-semibold text-[#E9ECF6] flex items-center gap-2 transition-all shadow-sm"
              title="Graph Tools, Metrics & Intelligence"
            >
              <Zap className="w-3.5 h-3.5 text-[#2FD9C4]" />
              <span>Tools & Metrics</span>
              <span id="toolsBadge" className="text-[10px] font-mono text-[#2FD9C4] px-1.5 py-0.2 rounded bg-[#2FD9C4]/10">
                5 KPIs · Active
              </span>
            </button>
          </div>

          {/* Theme Toggle */}
          <button
            id="themeToggleApp"
            onClick={toggleTheme}
            className="p-1.5 rounded-lg bg-[#111726] hover:bg-[#151C2E] border border-[#212B41] text-[#9AA3BC] hover:text-[#E9ECF6] transition-all"
            title="Toggle dark / light mode"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* Demo Mode Banner */}
      {isDemoMode && (
        <div id="demoApiBanner" className="flex items-center gap-2 px-4 py-1.5 bg-[#F2B84B]/10 border-b border-[#F2B84B]/20 text-xs text-[#F2B84B]">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>
            ⚠️ <strong>Hosted LLM API:</strong> Notes and queries are routed to <code id="demoApiProviderLabel">{apiProvider}</code>.
          </span>
        </div>
      )}

      {/* 2. Main Workbench Split */}
      <div ref={splitRef} className="flex-1 flex overflow-hidden relative">
        {/* Left Side: Note Editor */}
        <div
          id="splitEditorPane"
          style={{ width: `${splitRatio}%` }}
          className="h-full flex flex-col shrink-0 overflow-hidden"
        >
          <NoteEditor />
        </div>

        {/* Draggable Divider */}
        <div
          id="splitDivider"
          onMouseDown={() => setIsDraggingSplit(true)}
          className="w-1.5 hover:w-2 bg-[#1A2233] hover:bg-[#2FD9C4] cursor-col-resize flex items-center justify-center transition-all z-20 group"
          title="Drag to resize Editor and Canvas"
        >
          <div className="w-0.5 h-6 bg-[#5D6683] group-hover:bg-[#080B12] rounded-full" />
        </div>

        {/* Right Side: Graph Canvas */}
        <div
          id="splitGraphPane"
          style={{ width: `${100 - splitRatio}%` }}
          className="h-full flex flex-col overflow-hidden relative"
        >
          <GalaxyCanvas />
        </div>
      </div>

      {/* 3. Bottom Ask Bar & GraphRAG Chat Panel */}
      <div id="bottomBar" className="border-t border-[#1A2233] bg-[#0C111C] p-3 shrink-0 space-y-2 z-20">
        <div className="flex items-center justify-between gap-3 text-xs">
          {/* API Switcher */}
          <div className="api-switch flex items-center bg-[#111726] p-0.5 rounded-lg border border-[#212B41]">
            {(['auto', 'global', 'local'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setRagMode(m)}
                className={`px-2.5 py-0.5 rounded text-[11px] font-medium capitalize transition-all ${
                  ragMode === m ? 'bg-[#2FD9C4] text-[#080B12] font-semibold' : 'text-[#9AA3BC] hover:text-[#E9ECF6]'
                }`}
              >
                {m === 'auto' ? 'Auto Router' : m === 'global' ? 'Global GraphRAG' : 'Local Hybrid (FTS5)'}
              </button>
            ))}
          </div>

          <button
            id="analyzeBtn"
            onClick={() => openModal('communityReport')}
            className="px-3 py-1 rounded-lg bg-[#111726] hover:bg-[#151C2E] border border-[#212B41] text-[#A98CFB] flex items-center gap-1.5 transition-all"
          >
            <Boxes className="w-3.5 h-3.5" />
            <span>Inspect Community Summaries</span>
          </button>
        </div>

        {/* Ask Row Input */}
        <div className="ask-row flex gap-2">
          <input
            id="globalAsk"
            type="text"
            value={askQuery}
            onChange={(e) => setAskQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            placeholder="Ask across your whole graph (e.g. 'What are the main themes in my notes?')…"
            className="flex-1 px-3 py-2 text-xs rounded-xl bg-[#080B12] border border-[#212B41] text-[#E9ECF6] focus:outline-none focus:border-[#2FD9C4]"
          />
          <button
            id="globalAskBtn"
            onClick={handleAsk}
            disabled={isAsking || !askQuery.trim()}
            className="px-4 py-2 rounded-xl bg-[#2FD9C4] hover:bg-[#2FD9C4]/90 text-[#080B12] text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Send</span>
          </button>
        </div>

        {/* Chat Log Stream */}
        {chatMessages.length > 0 && (
          <div
            id="chatLog"
            className="max-h-28 overflow-y-auto p-2 rounded-xl bg-[#080B12] border border-[#212B41] text-xs space-y-2 font-body"
          >
            {chatMessages.map((m, idx) => (
              <div key={idx} className="flex gap-2">
                <span className={`font-semibold shrink-0 ${m.role === 'user' ? 'text-[#38BDF8]' : 'text-[#2FD9C4]'}`}>
                  {m.role === 'user' ? 'You:' : 'DriftGraph:'}
                </span>
                <span className="text-[#E9ECF6] leading-relaxed">{m.text}</span>
                {m.latency && <span className="text-[10px] text-[#5D6683] font-mono shrink-0">({m.latency}ms)</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 4. Modals Suite */}
      <ToolsDrawer />
      <VoiceModal />
      <OCRStudioModal />
      <ClassifierModal />
      <NotesGalleryModal />
      <TemplateModal />
      <WebScraperModal />
      <DeleteConfirmModal />
      <CommunityReportModal />
    </div>
  );
};
