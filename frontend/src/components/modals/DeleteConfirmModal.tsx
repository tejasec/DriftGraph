import React, { useState } from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { useNotesStore } from '@/stores/useNotesStore';
import { AlertTriangle, X } from 'lucide-react';

export const DeleteConfirmModal: React.FC = () => {
  const { activeModal, closeModal, deleteModalTarget } = useUIStore();
  const { deleteNote, bulkDelete } = useNotesStore();
  const [deleteType, setDeleteType] = useState<'soft' | 'permanent'>('soft');
  const [isDeleting, setIsDeleting] = useState(false);

  if (activeModal !== 'deleteConfirm' || !deleteModalTarget) return null;

  const isPermanent = deleteType === 'permanent';

  const handleConfirm = async () => {
    setIsDeleting(true);
    try {
      if (deleteModalTarget.noteIds.length === 1) {
        await deleteNote(deleteModalTarget.noteIds[0], isPermanent);
      } else {
        await bulkDelete(isPermanent);
      }
      closeModal();
    } catch (err: any) {
      alert(err.message || 'Deletion failed');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        id="modalDeleteConfirm"
        className="w-full max-w-md rounded-2xl bg-[#111726] border border-[#212B41] p-6 text-[#E9ECF6] shadow-2xl flex flex-col space-y-4 animate-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#F16565]/10 text-[#F16565] flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <span id="delModalEyebrow" className="text-[10px] text-[#F16565] font-mono uppercase tracking-wider block">
                Confirm Deletion
              </span>
              <h3 id="delModalTitle" className="font-semibold text-base">
                Delete {deleteModalTarget.noteIds.length > 1 ? `${deleteModalTarget.noteIds.length} Notes` : 'Note'}
              </h3>
            </div>
          </div>
          <button
            onClick={closeModal}
            className="p-1.5 rounded-lg bg-[#151C2E] text-[#9AA3BC] hover:text-[#E9ECF6]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p id="delModalMessage" className="text-xs text-[#9AA3BC] leading-relaxed">
          {deleteModalTarget.title
            ? `Are you sure you want to delete "${deleteModalTarget.title}"?`
            : `Are you sure you want to delete ${deleteModalTarget.noteIds.length} selected notes?`}
        </p>

        {/* Options */}
        <div className="space-y-2.5 p-3 rounded-xl bg-[#080B12] border border-[#212B41] text-xs">
          <label className="flex items-start gap-2.5 cursor-pointer">
            <input
              type="radio"
              name="delType"
              value="soft"
              checked={deleteType === 'soft'}
              onChange={() => setDeleteType('soft')}
              className="accent-[#2FD9C4] mt-0.5"
            />
            <div>
              <span className="font-semibold text-[#E9ECF6] block">Move to Trash (Soft Delete)</span>
              <span className="text-[11px] text-[#5D6683]">
                Safely removes from graph and search. Reversible with instant undo.
              </span>
            </div>
          </label>

          <label className="flex items-start gap-2.5 cursor-pointer pt-2 border-t border-[#1A2233]">
            <input
              type="radio"
              name="delType"
              value="permanent"
              checked={deleteType === 'permanent'}
              onChange={() => setDeleteType('permanent')}
              className="accent-[#F16565] mt-0.5"
            />
            <div>
              <span className="font-semibold text-[#F16565] block">Permanently Purge</span>
              <span className="text-[11px] text-[#5D6683]">
                Erases markdown, chunks, FAISS vector embeddings, and orphan nodes.
              </span>
            </div>
          </label>
        </div>

        {/* Buttons */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={closeModal}
            className="px-3 py-1.5 rounded-lg bg-[#151C2E] text-xs text-[#9AA3BC] hover:text-[#E9ECF6]"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isDeleting}
            className="px-4 py-1.5 rounded-lg bg-[#F16565] hover:bg-[#F16565]/90 text-white font-semibold text-xs transition-all shadow-sm disabled:opacity-50"
          >
            {isDeleting ? 'Deleting...' : 'Confirm Delete'}
          </button>
        </div>
      </div>
    </div>
  );
};
