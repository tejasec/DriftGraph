import React, { useState, useMemo } from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { useNotesStore } from '@/stores/useNotesStore';
import { Grid, X, Search, Plus, Trash2, Calendar, FileText } from 'lucide-react';

export const NotesGalleryModal: React.FC = () => {
  const { activeModal, closeModal } = useUIStore();
  const {
    notes,
    selectNote,
    createNote,
    selectedNoteIds,
    toggleNoteSelection,
    selectAllNotes,
    clearSelection,
    bulkDelete,
  } = useNotesStore();

  const [query, setQuery] = useState('');

  if (activeModal !== 'notesModal') return null;

  const filtered = useMemo(() => {
    if (!query.trim()) return notes;
    const q = query.toLowerCase();
    return notes.filter(
      (n) =>
        n.title.toLowerCase().includes(q) ||
        n.preview.toLowerCase().includes(q) ||
        n.tags.some((t) => t.toLowerCase().includes(q))
    );
  }, [notes, query]);

  const handleSelectNoteAndClose = (id: string) => {
    selectNote(id);
    closeModal();
  };

  const handleNewNoteAndClose = async () => {
    await createNote('Untitled Note', '');
    closeModal();
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        id="modalNotes"
        className="w-full max-w-4xl rounded-2xl bg-[#111726] border border-[#212B41] p-6 text-[#E9ECF6] shadow-2xl flex flex-col space-y-4 max-h-[88vh] overflow-hidden animate-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#2FD9C4]/10 text-[#2FD9C4] flex items-center justify-center">
              <Grid className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] text-[#2FD9C4] font-mono uppercase tracking-wider block">
                Notes Repository
              </span>
              <h3 className="font-semibold text-base">All Notes & Documents</h3>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              id="modalNewNoteBtn"
              onClick={handleNewNoteAndClose}
              className="px-3 py-1.5 rounded-lg bg-[#2FD9C4] text-[#080B12] text-xs font-semibold flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Note</span>
            </button>
            <button
              onClick={closeModal}
              className="p-1.5 rounded-lg bg-[#151C2E] text-[#9AA3BC] hover:text-[#E9ECF6]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Top Search & Filter Bar */}
        <div className="flex items-center gap-3 p-3 rounded-xl bg-[#080B12] border border-[#212B41] text-xs">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#5D6683]" />
            <input
              id="modalNotesSearchInput"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search notes by title, tag, or content..."
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-[#151C2E] border border-[#212B41] text-[#E9ECF6] focus:outline-none focus:border-[#2FD9C4]"
            />
          </div>
          <label className="flex items-center gap-1.5 cursor-pointer text-[#9AA3BC] shrink-0">
            <input
              id="modalSelectAllCheck"
              type="checkbox"
              checked={selectedNoteIds.length === filtered.length && filtered.length > 0}
              onChange={(e) => selectAllNotes(e.target.checked)}
              className="accent-[#2FD9C4]"
            />
            <span>Select All</span>
          </label>
          <span id="notesCountLabel" className="font-mono text-[#5D6683] shrink-0">
            {filtered.length} notes
          </span>
        </div>

        {/* Notes Cards Grid */}
        <div id="notesGrid" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 flex-1 overflow-y-auto pr-1">
          {filtered.map((n) => (
            <div
              key={n.id}
              onClick={() => handleSelectNoteAndClose(n.id)}
              className="p-4 rounded-xl bg-[#080B12]/80 hover:bg-[#151C2E] border border-[#212B41] hover:border-[#2FD9C4]/50 cursor-pointer transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <input
                      type="checkbox"
                      checked={selectedNoteIds.includes(n.id)}
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => toggleNoteSelection(n.id)}
                      className="accent-[#2FD9C4] shrink-0"
                    />
                    <h4 className="font-semibold text-xs text-[#E9ECF6] group-hover:text-[#2FD9C4] truncate transition-colors">
                      {n.title}
                    </h4>
                  </div>
                </div>
                <p className="text-[11px] text-[#9AA3BC] line-clamp-3 leading-relaxed mb-3">
                  {n.preview}
                </p>
              </div>

              <div className="flex items-center justify-between text-[10px] text-[#5D6683] font-mono pt-2 border-t border-[#1A2233]">
                <span>{n.word_count} words</span>
                <span>{n.date}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Modal Batch Bar */}
        {selectedNoteIds.length > 0 && (
          <div
            id="modalBatchBar"
            className="flex items-center justify-between p-3 rounded-xl bg-[#080B12] border border-[#212B41] text-xs"
          >
            <span id="modalBatchCount" className="text-[#2FD9C4] font-medium">
              {selectedNoteIds.length} notes selected
            </span>
            <div className="flex gap-2">
              <button
                id="modalBatchDeleteBtn"
                onClick={() => bulkDelete(false)}
                className="px-3 py-1.5 rounded-lg bg-[#F16565] text-white font-medium text-xs shadow-sm"
              >
                Delete Selected
              </button>
              <button
                id="modalBatchClearBtn"
                onClick={clearSelection}
                className="px-3 py-1.5 rounded-lg bg-[#151C2E] text-[#9AA3BC] hover:text-[#E9ECF6] text-xs"
              >
                Clear
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
