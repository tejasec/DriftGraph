import React, { useState, useRef } from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { useNotesStore } from '@/stores/useNotesStore';
import { useGraphStore } from '@/stores/useGraphStore';
import { voiceApi } from '@/api/client';
import { VoiceResponse } from '@/types/modals';
import { Mic, X, Volume2, Save, Send, Sparkles } from 'lucide-react';

export const VoiceModal: React.FC = () => {
  const { activeModal, closeModal } = useUIStore();
  const { createNote } = useNotesStore();
  const { setSelectedNodeId } = useGraphStore();

  const [query, setQuery] = useState('');
  const [quickAnswer, setQuickAnswer] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<VoiceResponse | null>(null);

  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  if (activeModal !== 'voiceModal') return null;

  const handleStartRecording = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Please type your question.');
      return;
    }

    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;

    recognition.onstart = () => setIsRecording(true);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setQuery(transcript);
      setIsRecording(false);
      handleSend(transcript);
    };
    recognition.onerror = () => setIsRecording(false);
    recognition.onend = () => setIsRecording(false);

    recognitionRef.current = recognition;
    recognition.start();
  };

  const handleSend = async (customQuery?: string) => {
    const q = (customQuery || query).trim();
    if (!q) return;

    setIsLoading(true);
    try {
      const res = await voiceApi.ask({
        query: q,
        quick_answer: quickAnswer,
        mode: quickAnswer ? 'quick' : 'auto',
      });
      setResponse(res);

      if (res.cited_node_ids && res.cited_node_ids.length > 0) {
        setSelectedNodeId(res.cited_node_ids[0]);
      }
    } catch (err: any) {
      alert(err.message || 'Voice RAG failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePlayAudio = () => {
    if (!response) return;
    if (response.audio_url) {
      const audio = new Audio(response.audio_url);
      audio.play();
    } else if (response.audio_base64) {
      const audio = new Audio(`data:audio/mp3;base64,${response.audio_base64}`);
      audio.play();
    } else if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(response.text_answer || response.answer || '');
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleSaveAsNote = async () => {
    if (!response) return;
    const title = `Voice Note: ${response.query.slice(0, 30)}`;
    const content = `# Voice Query: ${response.query}\n\n**Synthesized Answer:**\n${response.text_answer || response.answer}\n\n---\n*Citations:* ${response.cited_node_ids?.join(', ') || 'None'}`;
    await createNote(title, content);
    closeModal();
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        id="modalVoice"
        className="w-full max-w-lg rounded-2xl bg-[#111726] border border-[#212B41] p-6 text-[#E9ECF6] shadow-2xl flex flex-col space-y-5 animate-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#FB7BA6]/10 text-[#FB7BA6] flex items-center justify-center">
              <Mic className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] text-[#FB7BA6] font-mono uppercase tracking-wider block">
                Audible RAG
              </span>
              <h3 className="font-semibold text-base">Voice Assistant RAG</h3>
            </div>
          </div>
          <button
            onClick={closeModal}
            className="p-1.5 rounded-lg bg-[#151C2E] text-[#9AA3BC] hover:text-[#E9ECF6]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Quick Answer Toggle */}
        <div className="flex items-center justify-between px-3 py-2 rounded-xl bg-[#080B12] border border-[#212B41] text-xs">
          <span className="text-[#9AA3BC]">⚡ Quick-Answer Mode (Direct Graph Lookup)</span>
          <input
            id="voiceQuickToggle"
            type="checkbox"
            checked={quickAnswer}
            onChange={(e) => setQuickAnswer(e.target.checked)}
            className="accent-[#2FD9C4]"
          />
        </div>

        {/* Center Mic Button & Stage */}
        <div className="flex flex-col items-center py-4">
          <button
            id="micBtn"
            onClick={handleStartRecording}
            className={`w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-xl ${
              isRecording
                ? 'bg-[#F16565] text-white animate-pulse scale-110 shadow-[#F16565]/40'
                : 'bg-gradient-to-tr from-[#2FD9C4] to-[#A98CFB] text-[#080B12] hover:scale-105 shadow-[#2FD9C4]/25'
            }`}
          >
            <Mic className="w-8 h-8" />
          </button>
          <span id="micCaption" className="text-xs text-[#9AA3BC] mt-3 font-mono">
            {isRecording ? 'Listening to speech...' : 'Tap to speak grounded query'}
          </span>
        </div>

        {/* Text Input Fallback */}
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Or type a question to ask your graph..."
            className="flex-1 px-3 py-2 text-xs rounded-xl bg-[#080B12] border border-[#212B41] text-[#E9ECF6] focus:outline-none focus:border-[#2FD9C4]"
          />
          <button
            onClick={() => handleSend()}
            disabled={isLoading || !query.trim()}
            className="px-4 py-2 rounded-xl bg-[#2FD9C4] hover:bg-[#2FD9C4]/90 text-[#080B12] text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Ask</span>
          </button>
        </div>

        {/* Synthesized Response Box */}
        {response && (
          <div
            id="voiceTranscript"
            className="p-4 rounded-xl bg-[#080B12] border border-[#212B41] space-y-2 text-xs leading-relaxed"
          >
            <div className="flex items-center justify-between text-[#2FD9C4] font-semibold text-[11px]">
              <span>Synthesized Graph Answer</span>
              <span className="font-mono text-[#9AA3BC]">{response.mode_used} mode</span>
            </div>
            <p className="text-[#E9ECF6]">{response.text_answer || response.answer}</p>

            <div className="flex gap-2 pt-2 border-t border-[#1A2233]">
              <button
                id="voicePlayAudioBtn"
                onClick={handlePlayAudio}
                className="px-2.5 py-1 rounded-lg bg-[#151C2E] hover:bg-[#212B41] text-[#E9ECF6] text-[11px] font-medium flex items-center gap-1"
              >
                <Volume2 className="w-3.5 h-3.5 text-[#38BDF8]" />
                <span>Play Audio</span>
              </button>
              <button
                id="voiceSaveNoteBtn"
                onClick={handleSaveAsNote}
                className="px-2.5 py-1 rounded-lg bg-[#151C2E] hover:bg-[#212B41] text-[#E9ECF6] text-[11px] font-medium flex items-center gap-1"
              >
                <Save className="w-3.5 h-3.5 text-[#2FD9C4]" />
                <span>Save as Note</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
