import React, { useState } from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { useNotesStore } from '@/stores/useNotesStore';
import { useGraphStore } from '@/stores/useGraphStore';
import { sourcesApi } from '@/api/client';
import { Globe, X, Sparkles } from 'lucide-react';

export const WebScraperModal: React.FC = () => {
  const { activeModal, closeModal } = useUIStore();
  const { fetchNotes, selectNote } = useNotesStore();
  const { fetchGraph } = useGraphStore();

  const [url, setUrl] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [autoClassify, setAutoClassify] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('');

  if (activeModal !== 'webScrapeModal') return null;

  const handleScrape = async () => {
    if (!url.trim()) return;

    setIsLoading(true);
    setStatus('Scraping web page and synthesizing clean Markdown...');
    try {
      const res = await sourcesApi.scrapeUrl({
        url: url.trim(),
        custom_title: customTitle.trim() || undefined,
        auto_classify: autoClassify,
      });

      setStatus('Web article ingested successfully into Knowledge Graph!');
      await fetchNotes();
      await fetchGraph();

      if (res && res.saved_note) {
        selectNote(res.saved_note.replace('.md', ''));
      }
      setTimeout(() => closeModal(), 1200);
    } catch (err: any) {
      setStatus(`Failed: ${err.message || 'Scraping error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        id="modalWebScrape"
        className="w-full max-w-md rounded-2xl bg-[#111726] border border-[#212B41] p-6 text-[#E9ECF6] shadow-2xl flex flex-col space-y-4 animate-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#2FD9C4]/10 text-[#2FD9C4] flex items-center justify-center">
              <Globe className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] text-[#2FD9C4] font-mono uppercase tracking-wider block">
                Multi-Source Ingestion
              </span>
              <h3 className="font-semibold text-base">Ingest Web Page into Graph</h3>
            </div>
          </div>
          <button
            onClick={closeModal}
            className="p-1.5 rounded-lg bg-[#151C2E] text-[#9AA3BC] hover:text-[#E9ECF6]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Inputs */}
        <div className="space-y-3 text-xs">
          <div>
            <label className="text-[11px] font-semibold text-[#9AA3BC] block mb-1">
              Article / Documentation URL
            </label>
            <input
              id="webScrapeUrlInput"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://en.wikipedia.org/wiki/Knowledge_graph"
              className="w-full px-3 py-2 rounded-xl bg-[#080B12] border border-[#212B41] text-[#E9ECF6] focus:outline-none focus:border-[#2FD9C4]"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-[#9AA3BC] block mb-1">
              Custom Title (Optional)
            </label>
            <input
              id="webScrapeTitleInput"
              type="text"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              placeholder="Leave empty to auto-extract..."
              className="w-full px-3 py-2 rounded-xl bg-[#080B12] border border-[#212B41] text-[#E9ECF6] focus:outline-none focus:border-[#2FD9C4]"
            />
          </div>

          <label className="flex items-center gap-2 text-xs text-[#9AA3BC] cursor-pointer pt-1">
            <input
              id="webScrapeAutoClassify"
              type="checkbox"
              checked={autoClassify}
              onChange={(e) => setAutoClassify(e.target.checked)}
              className="accent-[#2FD9C4]"
            />
            <span>Auto-classify topic & auto-tag</span>
          </label>
        </div>

        <button
          id="runWebScrapeBtn"
          onClick={handleScrape}
          disabled={isLoading || !url.trim()}
          className="w-full py-2.5 rounded-xl bg-[#2FD9C4] hover:bg-[#2FD9C4]/90 text-[#080B12] font-semibold text-xs shadow-md transition-all disabled:opacity-50"
        >
          {isLoading ? 'Scraping Page...' : 'Scrape & Ingest Note'}
        </button>

        {status && (
          <div id="webScrapeStatus" className="text-xs text-center text-[#2FD9C4] font-medium">
            {status}
          </div>
        )}
      </div>
    </div>
  );
};
