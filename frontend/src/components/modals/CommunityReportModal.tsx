import React from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { useGraphStore } from '@/stores/useGraphStore';
import { Boxes, X } from 'lucide-react';

export const CommunityReportModal: React.FC = () => {
  const { activeModal, closeModal, communityReportData } = useUIStore();
  const { communities, setSelectedNodeId } = useGraphStore();

  if (activeModal !== 'communityReport') return null;

  const data = communityReportData || {
    title: communities[0]?.name || 'Global Community Insights',
    summary:
      communities[0]?.summary ||
      'Leiden partitioning groups closely-related concepts into semantic communities. Explore your clusters below.',
    entities: communities[0]?.node_ids || [],
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        id="modalGraphrag"
        className="w-full max-w-xl rounded-2xl bg-[#111726] border border-[#212B41] p-6 text-[#E9ECF6] shadow-2xl flex flex-col space-y-4 max-h-[85vh] overflow-hidden animate-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#A98CFB]/10 text-[#A98CFB] flex items-center justify-center">
              <Boxes className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] text-[#A98CFB] font-mono uppercase tracking-wider block">
                GraphRAG Community Summary
              </span>
              <h3 id="grTitle" className="font-semibold text-base">
                {data.title}
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

        {/* Entities */}
        {data.entities && data.entities.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[11px] font-semibold text-[#9AA3BC] uppercase tracking-wider block">
              Member Concepts ({data.entities.length})
            </span>
            <div id="grEntities" className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
              {data.entities.map((nodeId, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setSelectedNodeId(nodeId);
                    closeModal();
                  }}
                  className="px-2 py-0.5 rounded-full text-[11px] bg-[#151C2E] hover:bg-[#212B41] text-[#2FD9C4] border border-[#212B41] transition-all"
                >
                  {nodeId}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Summary text */}
        <div
          id="grSummary"
          className="flex-1 overflow-y-auto p-4 rounded-xl bg-[#080B12] border border-[#212B41] text-xs leading-relaxed text-[#E9ECF6] whitespace-pre-line"
        >
          {data.summary}
        </div>
      </div>
    </div>
  );
};
