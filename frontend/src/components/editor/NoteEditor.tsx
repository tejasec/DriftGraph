import React, { useState, useEffect, useMemo } from 'react';
import { useNotesStore } from '@/stores/useNotesStore';
import { useUIStore } from '@/stores/useUIStore';
import { useGraphStore } from '@/stores/useGraphStore';
import { ocrApi } from '@/api/client';
import { marked } from 'marked';
import {
  Plus,
  Search,
  Grid,
  RefreshCw,
  Upload,
  Mic,
  Trash2,
  CheckSquare,
  Square,
  FileText,
  Calendar,
  Tag,
  Link as LinkIcon,
} from 'lucide-react';

export const NoteEditor: React.FC = () => {
  const {
    notes,
    activeNoteId,
    activeNoteDetail,
    activeNoteTitle,
    activeNoteContent,
    editMode,
    searchQuery,
    selectedNoteIds,
    sidebarTab,
    isSaving,
    autoLinkingStatus,
    fetchNotes,
    selectNote,
    createNote,
    saveCurrentNote,
    deleteNote,
    bulkDelete,
    emptyTrash,
    setEditMode,
    setSearchQuery,
    setSidebarTab,
    toggleNoteSelection,
    selectAllNotes,
    clearSelection,
    setActiveTitle,
    setActiveContent,
  } = useNotesStore();

  const { openModal } = useUIStore();
  const { fetchGraph, setSelectedNodeId } = useGraphStore();

  const [isRebuilding, setIsRebuilding] = useState(false);
  const [saveDebounceTimer, setSaveDebounceTimer] = useState<any>(null);

  // Auto-save debouncer
  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setActiveContent(val);

    if (saveDebounceTimer) clearTimeout(saveDebounceTimer);
    const timer = setTimeout(() => {
      saveCurrentNote();
    }, 800);
    setSaveDebounceTimer(timer);
  };

  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setActiveTitle(val);

    if (saveDebounceTimer) clearTimeout(saveDebounceTimer);
    const timer = setTimeout(() => {
      saveCurrentNote();
    }, 800);
    setSaveDebounceTimer(timer);
  };

  const handleRebuild = async () => {
    setIsRebuilding(true);
    try {
      await ocrApi.rebuildPipeline();
      await fetchGraph();
      await fetchNotes();
    } catch (err) {
      console.error('Failed to rebuild pipeline', err);
    } finally {
      setIsRebuilding(false);
    }
  };

  // Filtered notes for search dropdown and navigator
  const filteredNotes = useMemo(() => {
    if (!searchQuery.trim()) return notes;
    const q = searchQuery.toLowerCase();
    return notes.filter(
      (n) =>
        n.title.toLowerCase().includes(q) ||
        n.preview.toLowerCase().includes(q) ||
        n.tags.some((t) => t.toLowerCase().includes(q))
    );
  }, [notes, searchQuery]);

  // Markdown HTML
  const markdownHtml = useMemo(() => {
    try {
      return marked.parse(activeNoteContent || '*No content*');
    } catch {
      return activeNoteContent;
    }
  }, [activeNoteContent]);

  return (
    <div className="flex flex-col h-full bg-[#111726] border-r border-[#1A2233] text-[#E9ECF6] select-none overflow-hidden">
      {/* Top Search Row */}
      <div className="flex items-center gap-2 p-3 border-b border-[#1A2233] bg-[#0C111C]/60">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#5D6683]" />
          <input
            id="notesSearchInput"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notes by title, tag, or content..."
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg bg-[#151C2E] border border-[#212B41] text-[#E9ECF6] placeholder-[#5D6683] focus:outline-none focus:border-[#2FD9C4] transition-all"
          />
        </div>
        <button
          id="btn-add-note-top"
          onClick={() => createNote('Untitled Note', '')}
          className="px-3 py-1.5 rounded-lg bg-[#2FD9C4] hover:bg-[#2FD9C4]/90 text-[#080B12] text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Note</span>
        </button>
      </div>

      {/* Editor Toolbar */}
      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-[#1A2233] overflow-x-auto shrink-0 text-xs">
        <button
          id="newNoteBtn"
          onClick={() => createNote('Untitled Note', '')}
          className="px-2.5 py-1 rounded-md bg-[#151C2E] hover:bg-[#212B41] text-[#2FD9C4] border border-[#212B41] font-medium flex items-center gap-1 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New note</span>
        </button>

        <button
          id="browseAllNotesBtn"
          onClick={() => openModal('notesModal')}
          className="px-2.5 py-1 rounded-md bg-[#151C2E] hover:bg-[#212B41] text-[#9AA3BC] hover:text-[#E9ECF6] border border-[#212B41] font-medium flex items-center gap-1 shrink-0"
        >
          <Grid className="w-3.5 h-3.5" />
          <span>Browse All</span>
        </button>

        <button
          id="rebuildPipelineBtn"
          onClick={handleRebuild}
          disabled={isRebuilding}
          className="px-2.5 py-1 rounded-md bg-[#151C2E] hover:bg-[#212B41] text-[#9AA3BC] hover:text-[#E9ECF6] border border-[#212B41] font-medium flex items-center gap-1 shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRebuilding ? 'animate-spin text-[#2FD9C4]' : ''}`} />
          <span>Rebuild</span>
        </button>

        <button
          id="uploadOcrBtn"
          onClick={() => openModal('ocrModal')}
          className="px-2.5 py-1 rounded-md bg-[#151C2E] hover:bg-[#212B41] text-[#9AA3BC] hover:text-[#E9ECF6] border border-[#212B41] font-medium flex items-center gap-1 shrink-0"
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Upload</span>
        </button>

        <button
          id="voiceQueryBtn"
          onClick={() => openModal('voiceModal')}
          className="px-2.5 py-1 rounded-md bg-[#FB7BA6]/10 hover:bg-[#FB7BA6]/20 text-[#FB7BA6] border border-[#FB7BA6]/30 font-medium flex items-center gap-1 shrink-0"
        >
          <Mic className="w-3.5 h-3.5" />
          <span>Voice</span>
        </button>
      </div>

      {/* Subtabs: Note Editor vs Note Navigator */}
      <div className="flex border-b border-[#1A2233] bg-[#0C111C]/40 text-xs shrink-0">
        <button
          id="sidebarTabEditor"
          onClick={() => setSidebarTab('editor')}
          className={`flex-1 py-2 text-center font-medium border-b-2 transition-all ${
            sidebarTab === 'editor'
              ? 'border-[#2FD9C4] text-[#2FD9C4]'
              : 'border-transparent text-[#9AA3BC] hover:text-[#E9ECF6]'
          }`}
        >
          📝 Note Editor
        </button>
        <button
          id="sidebarTabNavigator"
          onClick={() => setSidebarTab('navigator')}
          className={`flex-1 py-2 text-center font-medium border-b-2 transition-all ${
            sidebarTab === 'navigator'
              ? 'border-[#2FD9C4] text-[#2FD9C4]'
              : 'border-transparent text-[#9AA3BC] hover:text-[#E9ECF6]'
          }`}
        >
          📚 Note Navigator ({notes.length})
        </button>
      </div>

      {/* Subtab 1: Note Editor Body */}
      {sidebarTab === 'editor' ? (
        <div id="editorMainView" className="flex-1 flex flex-col p-4 overflow-y-auto">
          {activeNoteId ? (
            <>
              {/* Note Title Input */}
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2.5 h-2.5 rounded-full bg-[#2FD9C4] shadow-sm" />
                <input
                  id="noteTitleInput"
                  type="text"
                  value={activeNoteTitle}
                  onChange={handleTitleChange}
                  placeholder="Note Title..."
                  className="flex-1 bg-transparent text-lg font-semibold text-[#E9ECF6] focus:outline-none border-b border-transparent focus:border-[#212B41] pb-1 transition-all"
                />
              </div>

              {/* Write vs Preview Mode Tabs */}
              <div className="flex items-center gap-1 mb-3 bg-[#151C2E] p-1 rounded-lg w-fit border border-[#212B41]">
                <button
                  onClick={() => setEditMode('write')}
                  className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                    editMode === 'write' ? 'bg-[#2FD9C4] text-[#080B12]' : 'text-[#9AA3BC] hover:text-[#E9ECF6]'
                  }`}
                >
                  Write
                </button>
                <button
                  onClick={() => setEditMode('preview')}
                  className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                    editMode === 'preview' ? 'bg-[#2FD9C4] text-[#080B12]' : 'text-[#9AA3BC] hover:text-[#E9ECF6]'
                  }`}
                >
                  Preview
                </button>
              </div>

              {/* Editor Surface */}
              <div id="editorSurface" className="flex-1 flex flex-col min-h-[220px]">
                {editMode === 'write' ? (
                  <textarea
                    id="noteTextarea"
                    value={activeNoteContent}
                    onChange={handleContentChange}
                    placeholder="Write markdown notes with [[wikilinks]] or concepts..."
                    className="w-full flex-1 p-3 rounded-xl bg-[#080B12] border border-[#212B41] text-[#E9ECF6] font-mono text-xs leading-relaxed focus:outline-none focus:border-[#2FD9C4]/60 resize-none"
                    spellCheck="false"
                  />
                ) : (
                  <div
                    id="notePreview"
                    dangerouslySetInnerHTML={{ __html: markdownHtml }}
                    className="w-full flex-1 p-4 rounded-xl bg-[#080B12] border border-[#212B41] text-[#E9ECF6] text-xs leading-relaxed overflow-y-auto prose prose-invert max-w-none"
                  />
                )}
              </div>

              {/* Auto-linking Status */}
              <div
                id="linkStatus"
                className="mt-3 flex items-center gap-1.5 text-[11px] font-mono text-[#2FD9C4]"
              >
                <LinkIcon className="w-3 h-3" />
                <span>{autoLinkingStatus || 'Ready for auto-linking'}</span>
              </div>

              {/* Related Knowledge Nodes */}
              {activeNoteDetail && activeNoteDetail.connected_entities.length > 0 && (
                <div className="mt-4 pt-3 border-t border-[#1A2233]">
                  <h4 className="text-xs font-semibold text-[#9AA3BC] mb-2 uppercase tracking-wider">
                    Related Concepts
                  </h4>
                  <div id="relatedList" className="flex flex-wrap gap-1.5">
                    {activeNoteDetail.connected_entities.map((ent, i) => (
                      <button
                        key={i}
                        onClick={() => setSelectedNodeId(ent.name)}
                        className="px-2 py-0.5 rounded-full text-[11px] bg-[#151C2E] hover:bg-[#212B41] text-[#2FD9C4] border border-[#212B41] transition-all"
                      >
                        {ent.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-[#5D6683]">
              <FileText className="w-10 h-10 mb-2 opacity-50" />
              <p className="text-xs mb-3">No note selected</p>
              <button
                onClick={() => createNote('Untitled Note', '')}
                className="px-3 py-1.5 rounded-lg bg-[#2FD9C4] text-[#080B12] text-xs font-semibold shadow-sm"
              >
                Create a Note
              </button>
            </div>
          )}
        </div>
      ) : (
        /* Subtab 2: Note Navigator */
        <div id="sidebarNavigatorView" className="flex-1 flex flex-col p-3 overflow-hidden">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#1A2233] text-xs text-[#9AA3BC]">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedNoteIds.length === filteredNotes.length && filteredNotes.length > 0}
                onChange={(e) => selectAllNotes(e.target.checked)}
                className="accent-[#2FD9C4]"
              />
              <span>Select All</span>
            </label>
            <button
              id="navEmptyTrashBtn"
              onClick={emptyTrash}
              className="text-[#F16565] hover:underline text-[11px]"
            >
              Empty Trash
            </button>
          </div>

          <div id="sidebarNoteList" className="flex-1 overflow-y-auto space-y-1.5 pr-1">
            {filteredNotes.map((n) => (
              <div
                key={n.id}
                onClick={() => selectNote(n.id)}
                className={`p-2.5 rounded-xl border cursor-pointer transition-all ${
                  activeNoteId === n.id
                    ? 'bg-[#151C2E] border-[#2FD9C4]/50'
                    : 'bg-[#080B12]/60 hover:bg-[#151C2E]/60 border-[#1A2233]'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <input
                      type="checkbox"
                      checked={selectedNoteIds.includes(n.id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        toggleNoteSelection(n.id);
                      }}
                      className="accent-[#2FD9C4] shrink-0"
                    />
                    <span className="font-semibold text-xs text-[#E9ECF6] truncate">{n.title}</span>
                  </div>
                  <span className="text-[10px] text-[#5D6683] font-mono shrink-0">{n.date}</span>
                </div>
                <p className="text-[11px] text-[#9AA3BC] line-clamp-2 mt-1 pl-5">{n.preview}</p>
              </div>
            ))}
          </div>

          {/* Sticky Batch Action Bar */}
          {selectedNoteIds.length > 0 && (
            <div
              id="sidebarBatchBar"
              className="mt-2 p-2 rounded-xl bg-[#0C111C] border border-[#212B41] flex items-center justify-between text-xs"
            >
              <span id="sidebarBatchCount" className="text-[#2FD9C4] font-medium">
                {selectedNoteIds.length} selected
              </span>
              <div className="flex gap-1.5">
                <button
                  id="sidebarBatchDeleteBtn"
                  onClick={() => bulkDelete(false)}
                  className="px-2 py-1 rounded bg-[#F16565] text-white font-medium text-[11px]"
                >
                  Delete Selected
                </button>
                <button
                  id="sidebarBatchClearBtn"
                  onClick={clearSelection}
                  className="px-2 py-1 rounded bg-[#151C2E] text-[#9AA3BC] text-[11px]"
                >
                  Clear
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
