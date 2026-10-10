import React, { useState, useEffect } from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { useNotesStore } from '@/stores/useNotesStore';
import { useGraphStore } from '@/stores/useGraphStore';
import { notesApi } from '@/api/client';
import { TemplateItem } from '@/types/notes';
import { LayoutTemplate, X, Sparkles } from 'lucide-react';

export const TemplateModal: React.FC = () => {
  const { activeModal, closeModal } = useUIStore();
  const { fetchNotes, selectNote } = useNotesStore();
  const { fetchGraph } = useGraphStore();

  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState('meeting');
  const [title, setTitle] = useState('');
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (activeModal === 'templateModal') {
      notesApi.listTemplates().then((tpls) => {
        setTemplates(tpls);
        if (tpls.length > 0) {
          setSelectedTemplateId(tpls[0].id);
        }
      });
    }
  }, [activeModal]);

  if (activeModal !== 'templateModal') return null;

  const currentTemplate = templates.find((t) => t.id === selectedTemplateId) || {
    id: selectedTemplateId,
    name: selectedTemplateId,
    description: 'Structured template',
    fields: [
      { name: 'attendees', label: 'Attendees / Key People', placeholder: 'e.g. Alice, Bob' },
      { name: 'agenda', label: 'Key Objectives & Agenda', placeholder: 'e.g. Discuss GraphRAG pipeline' },
      { name: 'decisions', label: 'Decisions & Next Actions', placeholder: 'e.g. Ship React 19 frontend' },
    ],
  };

  const handleFieldChange = (name: string, val: string) => {
    setFieldValues((prev) => ({ ...prev, [name]: val }));
  };

  const handleCreate = async () => {
    setIsLoading(true);
    try {
      const created = await notesApi.instantiateTemplate(
        selectedTemplateId,
        fieldValues,
        title || undefined
      );
      await fetchNotes();
      await fetchGraph();
      selectNote(created.id);
      closeModal();
    } catch (err: any) {
      alert(err.message || 'Failed to instantiate template');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        id="modalTemplate"
        className="w-full max-w-lg rounded-2xl bg-[#111726] border border-[#212B41] p-6 text-[#E9ECF6] shadow-2xl flex flex-col space-y-4 max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#2FD9C4]/10 text-[#2FD9C4] flex items-center justify-center">
              <LayoutTemplate className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] text-[#2FD9C4] font-mono uppercase tracking-wider block">
                Structured Templates
              </span>
              <h3 className="font-semibold text-base">Create Note from Template</h3>
            </div>
          </div>
          <button
            onClick={closeModal}
            className="p-1.5 rounded-lg bg-[#151C2E] text-[#9AA3BC] hover:text-[#E9ECF6]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Template Buttons Grid */}
        <div id="templateButtons" className="grid grid-cols-3 sm:grid-cols-5 gap-2">
          {[
            { id: 'meeting', label: '👥 Meeting' },
            { id: 'research', label: '🔬 Research' },
            { id: 'concept', label: '💡 Concept' },
            { id: 'daily_log', label: '📅 Daily Log' },
            { id: 'literature', label: '📚 Literature' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setSelectedTemplateId(t.id)}
              className={`py-2 px-2 rounded-xl text-xs font-medium border text-center transition-all ${
                selectedTemplateId === t.id
                  ? 'bg-[#2FD9C4]/15 border-[#2FD9C4] text-[#2FD9C4]'
                  : 'bg-[#080B12] border-[#212B41] text-[#9AA3BC] hover:text-[#E9ECF6]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Form Inputs */}
        <div className="space-y-3 flex-1 overflow-y-auto pr-1 text-xs">
          <div>
            <label className="text-[11px] font-semibold text-[#9AA3BC] block mb-1">Note Title</label>
            <input
              id="templateTitleInput"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Meeting / Concept Title..."
              className="w-full px-3 py-2 rounded-xl bg-[#080B12] border border-[#212B41] text-[#E9ECF6] focus:outline-none focus:border-[#2FD9C4]"
            />
          </div>

          <div id="templateFieldsContainer" className="space-y-3">
            {currentTemplate.fields?.map((f) => (
              <div key={f.name}>
                <label className="text-[11px] font-semibold text-[#9AA3BC] block mb-1">{f.label}</label>
                <textarea
                  value={fieldValues[f.name] || ''}
                  onChange={(e) => handleFieldChange(f.name, e.target.value)}
                  placeholder={f.placeholder || ''}
                  className="w-full h-18 p-2.5 rounded-xl bg-[#080B12] border border-[#212B41] text-[#E9ECF6] focus:outline-none focus:border-[#2FD9C4] resize-none"
                />
              </div>
            ))}
          </div>
        </div>

        <button
          id="instantiateTemplateBtn"
          onClick={handleCreate}
          disabled={isLoading}
          className="w-full py-2.5 rounded-xl bg-[#2FD9C4] hover:bg-[#2FD9C4]/90 text-[#080B12] font-semibold text-xs shadow-md transition-all disabled:opacity-50"
        >
          {isLoading ? 'Creating Note...' : 'Create & Ingest Note'}
        </button>
      </div>
    </div>
  );
};
