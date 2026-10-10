import React, { useState } from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { classifyApi } from '@/api/client';
import { ClassificationResult } from '@/types/modals';
import { FileText, X, Terminal, Copy, Check } from 'lucide-react';

export const ClassifierModal: React.FC = () => {
  const { activeModal, closeModal } = useUIStore();
  const [text, setText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ClassificationResult | null>(null);
  const [copied, setCopied] = useState(false);

  if (activeModal !== 'classifierModal') return null;

  const sampleLegal =
    'This agreement and contract specifies the indemnification, liability, and governing law. The breach of clause 4 shall lead to termination and arbitration under the jurisdiction of the court.';
  const sampleTech =
    'The microservice architecture uses FastAPI, SQLite database, FAISS vector embeddings, and a NetworkX graph pipeline to optimize query latency and backend runtime.';

  const handleClassify = async () => {
    if (!text.trim()) return;
    setIsLoading(true);
    try {
      const res = await classifyApi.classifyText(text);
      setResult(res);
    } catch (err: any) {
      alert(err.message || 'Classification failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyAscii = () => {
    if (!result?.ascii_box) return;
    navigator.clipboard.writeText(result.ascii_box);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        id="modalClassifier"
        className="w-full max-w-4xl rounded-2xl bg-[#111726] border border-[#212B41] p-6 text-[#E9ECF6] shadow-2xl flex flex-col space-y-4 max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#2FD9C4]/10 text-[#2FD9C4] flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] text-[#2FD9C4] font-mono uppercase tracking-wider block">
                Offline Rule-Based Intelligence
              </span>
              <h3 className="font-semibold text-base">Rule-Based Text Extraction & Classification Tool</h3>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              id="classifierSampleLegalBtn"
              onClick={() => setText(sampleLegal)}
              className="px-2.5 py-1 rounded-lg bg-[#151C2E] text-[11px] text-[#9AA3BC] hover:text-[#E9ECF6] border border-[#212B41]"
            >
              Sample Legal
            </button>
            <button
              id="classifierSampleTechBtn"
              onClick={() => setText(sampleTech)}
              className="px-2.5 py-1 rounded-lg bg-[#151C2E] text-[11px] text-[#9AA3BC] hover:text-[#E9ECF6] border border-[#212B41]"
            >
              Sample Tech
            </button>
            <button
              onClick={closeModal}
              className="p-1.5 rounded-lg bg-[#151C2E] text-[#9AA3BC] hover:text-[#E9ECF6]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Classifier Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 overflow-y-auto">
          {/* Left Column: Input and Category Breakdown */}
          <div className="space-y-3 flex flex-col">
            <textarea
              id="classifierInput"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste text or document excerpts here to classify..."
              className="w-full h-44 p-3 rounded-xl bg-[#080B12] border border-[#212B41] text-xs font-mono text-[#E9ECF6] focus:outline-none focus:border-[#2FD9C4] resize-none"
            />
            <button
              id="runClassifierBtn"
              onClick={handleClassify}
              disabled={isLoading || !text.trim()}
              className="py-2.5 rounded-xl bg-[#2FD9C4] hover:bg-[#2FD9C4]/90 text-[#080B12] text-xs font-semibold shadow-md transition-all disabled:opacity-50"
            >
              {isLoading ? 'Classifying...' : 'Classify Document'}
            </button>

            {/* Category Breakdown */}
            <div className="flex-1 p-3 rounded-xl bg-[#080B12] border border-[#212B41] space-y-2 text-xs overflow-y-auto">
              <span className="text-[11px] text-[#9AA3BC] font-semibold block">Detected Categories:</span>
              <div id="classifierBarsContainer" className="space-y-2">
                {result?.categories?.map((cat) => (
                  <div key={cat.category} className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="font-medium text-[#E9ECF6]">{cat.category}</span>
                      <span className="font-mono text-[#2FD9C4]">{cat.percentage.toFixed(1)}%</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-[#151C2E] overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[#2FD9C4] to-[#A98CFB]"
                        style={{ width: `${cat.percentage}%` }}
                      />
                    </div>
                  </div>
                )) || (
                  <span className="text-[11px] text-[#5D6683]">Run classification to see category breakdown.</span>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: ASCII Terminal Output */}
          <div className="flex flex-col space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono text-[#2FD9C4] flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5" />
                <span>TERMINAL OUTPUT</span>
              </span>
              <button
                id="copyAsciiBoxBtn"
                onClick={handleCopyAscii}
                className="px-2 py-1 rounded-md bg-[#151C2E] hover:bg-[#212B41] text-[11px] text-[#9AA3BC] flex items-center gap-1 border border-[#212B41]"
              >
                {copied ? <Check className="w-3 h-3 text-[#2FD9C4]" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied' : 'Copy ASCII Box'}</span>
              </button>
            </div>

            <pre
              id="asciiBoxOutput"
              className="flex-1 p-3 rounded-xl bg-[#080B12] border border-[#212B41] text-[10px] font-mono leading-relaxed text-[#2FD9C4] overflow-auto select-text whitespace-pre"
            >
              {result?.ascii_box ||
                `╔══════════════════════════════════════════════════════╗\n║       📄 Text Extraction & Classification Tool       ║\n║              Rule-Based · Fully Offline               ║\n╚══════════════════════════════════════════════════════╝\n\n(Click "Classify Document" to analyze document statistics)`}
            </pre>

            {/* Extra Metadata */}
            {result && (
              <div
                id="classifierExtraMetadata"
                className="p-3 rounded-xl bg-[#080B12] border border-[#212B41] text-[11px] text-[#9AA3BC] space-y-1"
              >
                <div>
                  <strong className="text-[#E9ECF6]">Top Category:</strong> {result.top_category}
                </div>
                <div>
                  <strong className="text-[#E9ECF6]">Sentiment:</strong> {result.sentiment} (
                  {result.sentiment_score.toFixed(2)}) · <strong className="text-[#E9ECF6]">Priority:</strong>{' '}
                  {result.priority}
                </div>
                {result.auto_tags.length > 0 && (
                  <div>
                    <strong className="text-[#E9ECF6]">Auto Tags:</strong> {result.auto_tags.join(', ')}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
