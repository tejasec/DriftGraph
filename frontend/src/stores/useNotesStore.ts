import { create } from 'zustand';
import { NoteSummary, NoteDetail } from '@/types/notes';
import { notesApi } from '@/api/client';

interface NotesState {
  notes: NoteSummary[];
  activeNoteId: string | null;
  activeNoteDetail: NoteDetail | null;
  activeNoteTitle: string;
  activeNoteContent: string;
  editMode: 'write' | 'preview';
  searchQuery: string;
  selectedNoteIds: string[];
  sidebarTab: 'editor' | 'navigator';
  isLoading: boolean;
  isSaving: boolean;
  autoLinkingStatus: string;

  fetchNotes: (includeDeleted?: boolean) => Promise<void>;
  selectNote: (noteId: string) => Promise<void>;
  createNote: (title?: string, content?: string) => Promise<NoteDetail>;
  saveCurrentNote: () => Promise<void>;
  deleteNote: (noteId: string, permanent?: boolean) => Promise<void>;
  bulkDelete: (permanent?: boolean) => Promise<void>;
  undoDelete: (noteId: string) => Promise<void>;
  emptyTrash: () => Promise<void>;
  setEditMode: (mode: 'write' | 'preview') => void;
  setSearchQuery: (q: string) => void;
  setSidebarTab: (tab: 'editor' | 'navigator') => void;
  toggleNoteSelection: (id: string) => void;
  selectAllNotes: (select: boolean) => void;
  clearSelection: () => void;
  setActiveTitle: (title: string) => void;
  setActiveContent: (content: string) => void;
}

export const useNotesStore = create<NotesState>((set, get) => ({
  notes: [],
  activeNoteId: null,
  activeNoteDetail: null,
  activeNoteTitle: '',
  activeNoteContent: '',
  editMode: 'write',
  searchQuery: '',
  selectedNoteIds: [],
  sidebarTab: 'editor',
  isLoading: false,
  isSaving: false,
  autoLinkingStatus: '',

  fetchNotes: async (includeDeleted = false) => {
    set({ isLoading: true });
    try {
      const data = await notesApi.listNotes(includeDeleted);
      set({ notes: data || [], isLoading: false });
    } catch (err) {
      console.error('Failed to fetch notes', err);
      set({ isLoading: false });
    }
  },

  selectNote: async (noteId: string) => {
    set({ isLoading: true, activeNoteId: noteId });
    try {
      const detail = await notesApi.getNote(noteId);
      set({
        activeNoteDetail: detail,
        activeNoteTitle: detail.title,
        activeNoteContent: detail.content,
        isLoading: false,
        autoLinkingStatus: detail.connected_entities.length > 0
          ? `Linked to ${detail.connected_entities.length} knowledge node${detail.connected_entities.length > 1 ? 's' : ''}`
          : 'Ready for auto-linking',
      });
    } catch (err) {
      console.error('Failed to get note detail', err);
      set({ isLoading: false });
    }
  },

  createNote: async (title = 'Untitled Note', content = '') => {
    set({ isSaving: true });
    try {
      const newNote = await notesApi.createNote({ title, content });
      await get().fetchNotes();
      set({
        activeNoteId: newNote.id,
        activeNoteDetail: newNote,
        activeNoteTitle: newNote.title,
        activeNoteContent: newNote.content,
        isSaving: false,
        sidebarTab: 'editor',
      });
      return newNote;
    } catch (err) {
      console.error('Failed to create note', err);
      set({ isSaving: false });
      throw err;
    }
  },

  saveCurrentNote: async () => {
    const { activeNoteId, activeNoteTitle, activeNoteContent } = get();
    if (!activeNoteId) return;

    set({ isSaving: true });
    try {
      const updated = await notesApi.updateNote(activeNoteId, {
        title: activeNoteTitle,
        content: activeNoteContent,
      });
      set({
        activeNoteDetail: updated,
        isSaving: false,
        autoLinkingStatus: updated.connected_entities.length > 0
          ? `Auto-linked: ${updated.connected_entities.length} concepts connected`
          : 'Saved',
      });
      await get().fetchNotes();
    } catch (err) {
      console.error('Failed to save note', err);
      set({ isSaving: false, autoLinkingStatus: 'Error saving note' });
    }
  },

  deleteNote: async (noteId: string, permanent = false) => {
    try {
      await notesApi.deleteNote(noteId, permanent);
      if (get().activeNoteId === noteId) {
        set({
          activeNoteId: null,
          activeNoteDetail: null,
          activeNoteTitle: '',
          activeNoteContent: '',
        });
      }
      await get().fetchNotes();
    } catch (err) {
      console.error('Failed to delete note', err);
    }
  },

  bulkDelete: async (permanent = false) => {
    const { selectedNoteIds } = get();
    if (selectedNoteIds.length === 0) return;

    try {
      await notesApi.bulkDelete(selectedNoteIds, permanent);
      set({ selectedNoteIds: [] });
      await get().fetchNotes();
    } catch (err) {
      console.error('Failed to bulk delete', err);
    }
  },

  undoDelete: async (noteId: string) => {
    try {
      await notesApi.undoDelete(noteId);
      await get().fetchNotes();
    } catch (err) {
      console.error('Failed to undo delete', err);
    }
  },

  emptyTrash: async () => {
    try {
      await notesApi.emptyTrash();
      await get().fetchNotes();
    } catch (err) {
      console.error('Failed to empty trash', err);
    }
  },

  setEditMode: (mode: 'write' | 'preview') => set({ editMode: mode }),
  setSearchQuery: (q: string) => set({ searchQuery: q }),
  setSidebarTab: (tab: 'editor' | 'navigator') => set({ sidebarTab: tab }),

  toggleNoteSelection: (id: string) => {
    const current = get().selectedNoteIds;
    if (current.includes(id)) {
      set({ selectedNoteIds: current.filter((item) => item !== id) });
    } else {
      set({ selectedNoteIds: [...current, id] });
    }
  },

  selectAllNotes: (select: boolean) => {
    if (select) {
      const allIds = get().notes.map((n) => n.id);
      set({ selectedNoteIds: allIds });
    } else {
      set({ selectedNoteIds: [] });
    }
  },

  clearSelection: () => set({ selectedNoteIds: [] }),
  setActiveTitle: (title: string) => set({ activeNoteTitle: title }),
  setActiveContent: (content: string) => set({ activeNoteContent: content }),
}));
