import React, { useState, useRef } from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { useNotesStore } from '@/stores/useNotesStore';
import { useGraphStore } from '@/stores/useGraphStore';
import { ocrApi } from '@/api/client';
import { BatchUploadResponse } from '@/types/modals';
import { FileScan, X, Upload, CheckCircle2, AlertCircle, FileText, Table } from 'lucide-react';

export const OCRStudioModal: React.FC = () => {
  const { activeModal, closeModal } = useUIStore();
  const { fetchNotes } = useNotesStore();
  const { fetchGraph } = useGraphStore();

  const [engine, setEngine] = useState('tesseract');
  const [lang, setLang] = useState('eng');
  const [speedMode, setSpeedMode] = useState('balanced');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [activeTab, setActiveTab] = useState<'highlights' | 'markdown' | 'errors'>('highlights');
  const [result, setResult] = useState<BatchUploadResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  if (activeModal !== 'ocrModal') return null;

  const handleFilesSelected = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setIsProcessing(true);
    setProgressPercent(20);

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    formData.append('engine', engine);
    formData.append('lang', lang);
    formData.append('speed_mode', speedMode);

    try {
      setProgressPercent(50);
      const res = await ocrApi.uploadDocuments(formData);
      setProgressPercent(100);
      setResult(res);
      await fetchNotes();
      await fetchGraph();
    } catch (err: any) {
      alert(err.message || 'OCR processing failed');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        id="modalOcr"
        className="w-full max-w-2xl rounded-2xl bg-[#111726] border border-[#212B41] p-6 text-[#E9ECF6] shadow-2xl flex flex-col space-y-4 max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#2FD9C4]/10 text-[#2FD9C4] flex items-center justify-center">
              <FileScan className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] text-[#2FD9C4] font-mono uppercase tracking-wider block">
                Digital Document Studio
              </span>
              <h3 className="font-semibold text-base">Scan, Highlight & Ingest Documents</h3>
            </div>
          </div>
          <button
            onClick={closeModal}
            className="p-1.5 rounded-lg bg-[#151C2E] text-[#9AA3BC] hover:text-[#E9ECF6]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* OCR Controls Bar */}
        <div className="grid grid-cols-3 gap-2.5 p-3 rounded-xl bg-[#080B12] border border-[#212B41] text-xs">
          <div>
            <label className="text-[10px] text-[#9AA3BC] block mb-1">OCR Engine:</label>
            <select
              id="ocrEngineSelect"
              value={engine}
              onChange={(e) => setEngine(e.target.value)}
              className="w-full px-2 py-1.5 rounded-lg bg-[#151C2E] border border-[#212B41] text-[#E9ECF6] text-xs focus:outline-none"
            >
              <option value="tesseract">Tesseract (Local 5.5)</option>
              <option value="google_vision">Google Vision (Cloud)</option>
              <option value="local">Local Heuristic (Fast)</option>
            </select>
          </div>

          <div>
            <label className="text-[10px] text-[#9AA3BC] block mb-1">Language:</label>
            <select
              id="ocrLangSelect"
              value={lang}
              onChange={(e) => setLang(e.target.value)}
              className="w-full px-2 py-1.5 rounded-lg bg-[#151C2E] border border-[#212B41] text-[#E9ECF6] text-xs focus:outline-none"
            >
              <option value="eng">English (eng)</option>
              <option value="spa">Spanish (spa)</option>
              <option value="chi_sim">Chinese Simp (chi_sim)</option>
              <option value="jpn">Japanese (jpn)</option>
              <option value="fra">French (fra)</option>
              <option value="deu">German (deu)</option>
              <option value="lat">Latin (lat)</option>
            </select>
          </div>

          <div>
            <label className="text-[10px] text-[#9AA3BC] block mb-1">Speed Profile:</label>
            <div id="ocrSpeedGroup" className="flex gap-1">
              {['fast', 'balanced', 'accurate'].map((s) => (
                <button
                  key={s}
                  onClick={() => setSpeedMode(s)}
                  className={`flex-1 py-1 rounded-md text-[10px] font-medium capitalize border transition-all ${
                    speedMode === s
                      ? 'bg-[#2FD9C4]/15 border-[#2FD9C4] text-[#2FD9C4]'
                      : 'bg-[#151C2E] border-[#212B41] text-[#9AA3BC]'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Dropzone */}
        <div
          id="dropzone"
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-[#212B41] hover:border-[#2FD9C4]/60 rounded-xl p-6 text-center cursor-pointer transition-all bg-[#080B12]/40 hover:bg-[#151C2E]/40"
        >
          <Upload className="w-8 h-8 text-[#2FD9C4] mx-auto mb-2" />
          <span id="dropzoneLabel" className="text-xs text-[#E9ECF6] font-medium block">
            Upload PDF or Document (.pdf, images, .md, .txt) — batch upload supported
          </span>
          <span className="text-[11px] text-[#5D6683] mt-1 block">Click or drag & drop files here</span>
          <input
            id="noteFileInput"
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp,.webp,.md,.markdown,.txt,text/plain"
            onChange={(e) => handleFilesSelected(e.target.files)}
            className="hidden"
          />
        </div>

        {/* Batch Progress Bar */}
        {isProcessing && (
          <div id="batchProgressWrap" className="space-y-1 text-xs">
            <div className="flex justify-between text-[#9AA3BC]">
              <span id="batchStatusLabel">Extracting and indexing text layers...</span>
              <span id="batchPercentLabel">{progressPercent}%</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-[#151C2E] overflow-hidden">
              <div
                id="batchProgressFill"
                className="h-full bg-[#2FD9C4] transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}

        {/* OCR Result Viewer */}
        {result && (
          <div id="ocrResult" className="flex-1 overflow-y-auto space-y-3 pt-2">
            <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-[#080B12] border border-[#212B41]">
              <span className="font-semibold text-[#2FD9C4]">{result.message}</span>
              <span className="text-[#9AA3BC] font-mono">
                {result.successful_documents} docs · {result.total_pages} pages · Conf: {result.mean_confidence}%
              </span>
            </div>

            {/* Result Tabs */}
            <div className="flex gap-2 border-b border-[#212B41] pb-2 text-xs">
              <button
                onClick={() => setActiveTab('highlights')}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${
                  activeTab === 'highlights' ? 'bg-[#2FD9C4] text-[#080B12]' : 'text-[#9AA3BC]'
                }`}
              >
                Processed Documents ({result.documents.length})
              </button>
            </div>

            <div className="space-y-1.5 max-h-[160px] overflow-y-auto pr-1">
              {result.documents.map((doc, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-[#080B12] border border-[#212B41] text-xs"
                >
                  <div className="flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-[#2FD9C4]" />
                    <span className="font-medium">{doc.filename}</span>
                  </div>
                  <span className="text-[11px] text-[#9AA3BC] font-mono">
                    {doc.pages_count}p · {doc.mean_confidence}% conf
                  </span>
                </div>
              ))}
            </div>

            <button
              id="ocrAddBtn"
              onClick={closeModal}
              className="w-full py-2.5 rounded-xl bg-[#2FD9C4] hover:bg-[#2FD9C4]/90 text-[#080B12] font-semibold text-xs shadow-md transition-all"
            >
              Done · Added to Knowledge Graph & Index
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
