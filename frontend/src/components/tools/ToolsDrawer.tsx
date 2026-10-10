import React, { useEffect } from 'react';
import { useAnalyticsStore } from '@/stores/useAnalyticsStore';
import { useGraphStore } from '@/stores/useGraphStore';
import { useUIStore } from '@/stores/useUIStore';
import {
  X,
  RefreshCw,
  Compass,
  Zap,
  HelpCircle,
  GitPullRequest,
  Sliders,
  Settings,
  Sparkles,
  Layers,
  Maximize2,
  FileText,
  Mic,
  Upload,
  Download,
} from 'lucide-react';

export const ToolsDrawer: React.FC = () => {
  const {
    report,
    pathResult,
    pathSource,
    pathTarget,
    isFindingPath,
    isLoading,
    fetchReport,
    findPath,
    setPathSource,
    setPathTarget,
  } = useAnalyticsStore();

  const {
    nodes,
    edges,
    communities,
    coulombRepulsion,
    springTension,
    similarityThreshold,
    setCoulombRepulsion,
    setSpringTension,
    setSimilarityThreshold,
    recomputeLayout,
    setActiveCommunityLevel,
    activeCommunityLevel,
  } = useGraphStore();

  const { activeModal, closeModal, openModal } = useUIStore();

  useEffect(() => {
    if (activeModal === 'toolsDrawer') {
      fetchReport();
    }
  }, [activeModal, fetchReport]);

  if (activeModal !== 'toolsDrawer') return null;

  const handleTracePath = () => {
    if (pathSource && pathTarget) {
      findPath(pathSource, pathTarget);
    }
  };

  const handleExportJson = () => {
    const data = JSON.stringify({ nodes, edges, communities }, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `driftgraph_export_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      {/* Backdrop */}
      <div
        id="toolsDrawerBackdrop"
        onClick={closeModal}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
      />

      {/* Drawer Surface */}
      <aside
        id="toolsDrawer"
        className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-[#0C111C] border-l border-[#212B41] z-50 flex flex-col text-[#E9ECF6] shadow-2xl overflow-hidden animate-in slide-in-from-right duration-300"
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#1A2233] bg-[#111726]/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#2FD9C4]/10 text-[#2FD9C4] flex items-center justify-center">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-sm">Graph Intelligence & Tools Studio</h3>
              <p className="text-[11px] text-[#9AA3BC]">Live topology, God nodes & path navigation</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              id="refreshAnalyticsBtn"
              onClick={fetchReport}
              disabled={isLoading}
              className="p-1.5 rounded-lg bg-[#151C2E] hover:bg-[#212B41] text-[#9AA3BC] hover:text-[#E9ECF6] transition-all"
              title="Refresh metrics"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-[#2FD9C4]' : ''}`} />
            </button>
            <button
              id="closeToolsDrawerBtn"
              onClick={closeModal}
              className="p-1.5 rounded-lg bg-[#151C2E] hover:bg-[#212B41] text-[#9AA3BC] hover:text-[#E9ECF6] transition-all"
              title="Close drawer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Drawer Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Section 1: Vital Statistics KPIs */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#34D399] uppercase tracking-wider">
              <span>📊 Vital Statistics</span>
            </div>
            <div id="analyticsKpis" className="grid grid-cols-3 gap-2">
              <div className="p-3 rounded-xl bg-[#111726] border border-[#212B41] text-center">
                <span className="text-[10px] text-[#9AA3BC] block mb-0.5">Nodes</span>
                <span id="kpiNodes" className="text-base font-bold text-[#E9ECF6]">
                  {report?.node_count ?? nodes.length}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[#111726] border border-[#212B41] text-center">
                <span className="text-[10px] text-[#9AA3BC] block mb-0.5">Edges</span>
                <span id="kpiEdges" className="text-base font-bold text-[#E9ECF6]">
                  {report?.edge_count ?? edges.length}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[#111726] border border-[#212B41] text-center">
                <span className="text-[10px] text-[#9AA3BC] block mb-0.5">Clusters</span>
                <span id="kpiComms" className="text-base font-bold text-[#E9ECF6]">
                  {report?.community_count ?? communities.length}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-[#111726] border border-[#212B41] text-center">
                <span className="text-[10px] text-[#9AA3BC] block mb-0.5">Density</span>
                <span id="kpiDensity" className="text-sm font-bold text-[#E9ECF6]">
                  {report ? `${(report.density * 100).toFixed(1)}%` : '--'}
                </span>
              </div>
              <div className="col-span-2 p-3 rounded-xl bg-[#111726] border border-[#212B41] text-center">
                <span className="text-[10px] text-[#9AA3BC] block mb-0.5">Connectivity</span>
                <span id="kpiConn" className="text-xs font-semibold text-[#2FD9C4]">
                  {report?.is_connected ? 'Unified Graph' : 'Multiple Components'}
                </span>
              </div>
            </div>
          </div>

          {/* Section 2: Path Explorer */}
          <div className="space-y-2.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#F2B84B] uppercase tracking-wider">
              <Compass className="w-3.5 h-3.5" />
              <span>🧭 Path Explorer ("What connects X to Y?")</span>
            </div>
            <div className="p-3 rounded-xl bg-[#111726] border border-[#212B41] space-y-2.5">
              <div className="space-y-2">
                <input
                  id="pathSourceInput"
                  value={pathSource}
                  onChange={(e) => setPathSource(e.target.value)}
                  placeholder="Source concept (e.g. SBERT)"
                  className="w-full px-3 py-1.5 text-xs rounded-lg bg-[#151C2E] border border-[#212B41] text-[#E9ECF6] placeholder-[#5D6683] focus:outline-none focus:border-[#F2B84B]"
                />
                <input
                  id="pathTargetInput"
                  value={pathTarget}
                  onChange={(e) => setPathTarget(e.target.value)}
                  placeholder="Target concept (e.g. Leiden)"
                  className="w-full px-3 py-1.5 text-xs rounded-lg bg-[#151C2E] border border-[#212B41] text-[#E9ECF6] placeholder-[#5D6683] focus:outline-none focus:border-[#F2B84B]"
                />
                <button
                  id="tracePathBtn"
                  onClick={handleTracePath}
                  disabled={isFindingPath}
                  className="w-full py-2 rounded-lg bg-[#F2B84B] hover:bg-[#F2B84B]/90 text-[#080B12] font-semibold text-xs transition-all shadow-sm flex items-center justify-center gap-1.5"
                >
                  {isFindingPath ? 'Tracing Path...' : 'Trace Navigation Path'}
                </button>
              </div>

              <div
                id="pathResultBox"
                className="p-3 rounded-lg bg-[#080B12] border border-[#212B41] text-xs leading-relaxed text-[#9AA3BC]"
              >
                {pathResult ? (
                  <div>
                    <div className="font-semibold text-[#E9ECF6] mb-1">
                      {pathResult.path_found ? `Found Path (${pathResult.hops} hops):` : 'No direct connection:'}
                    </div>
                    <p className="text-[11px] text-[#2FD9C4] font-mono mb-2">
                      {pathResult.node_sequence?.join(' ➔ ') || 'N/A'}
                    </p>
                    <p className="text-[11px]">{pathResult.narrative}</p>
                  </div>
                ) : (
                  'Enter two concepts above to discover how they connect across relationships.'
                )}
              </div>
            </div>
          </div>

          {/* Section 3: God Nodes */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#A98CFB] uppercase tracking-wider">
              <Zap className="w-3.5 h-3.5" />
              <span>⚡ God Nodes (Central Nexus Entities)</span>
            </div>
            <div id="godNodesList" className="space-y-2">
              {report?.god_nodes?.slice(0, 4).map((gn) => (
                <div key={gn.id} className="p-3 rounded-xl bg-[#111726] border border-[#212B41]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-xs text-[#E9ECF6]">{gn.name}</span>
                    <span className="text-[10px] font-mono text-[#A98CFB] px-1.5 py-0.5 rounded bg-[#A98CFB]/10">
                      Degree: {gn.degree}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#9AA3BC] leading-relaxed">{gn.explanation}</p>
                </div>
              )) || (
                <div className="text-xs text-[#5D6683] p-2">Analyzing centrality metrics...</div>
              )}
            </div>
          </div>

          {/* Section 4: Emergent Questions */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#5B8DEF] uppercase tracking-wider">
              <HelpCircle className="w-3.5 h-3.5" />
              <span>💡 Emergent Boundary Questions</span>
            </div>
            <div id="suggestedQuestionsList" className="space-y-2">
              {report?.suggested_questions?.slice(0, 3).map((q, i) => (
                <div key={i} className="p-3 rounded-xl bg-[#111726] border border-[#212B41]">
                  <p className="text-xs font-medium text-[#E9ECF6] mb-1">"{q.question}"</p>
                  <p className="text-[10px] text-[#9AA3BC]">{q.rationale}</p>
                </div>
              )) || (
                <div className="text-xs text-[#5D6683] p-2">Scanning community tensions...</div>
              )}
            </div>
          </div>

          {/* Section 5: Surprising Bridges */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#FB7BA6] uppercase tracking-wider">
              <GitPullRequest className="w-3.5 h-3.5" />
              <span>🔀 Surprising Cross-Community Bridges</span>
            </div>
            <div id="surprisingBridgesList" className="space-y-2">
              {report?.surprising_connections?.slice(0, 3).map((sc, i) => (
                <div key={i} className="p-3 rounded-xl bg-[#111726] border border-[#212B41]">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-[#E9ECF6] mb-1">
                    <span>{sc.source_name}</span>
                    <span className="text-[#FB7BA6] text-[10px]">({sc.relation})</span>
                    <span>{sc.target_name}</span>
                  </div>
                  <p className="text-[10px] text-[#9AA3BC]">{sc.rationale}</p>
                </div>
              )) || (
                <div className="text-xs text-[#5D6683] p-2">Scanning bridge links...</div>
              )}
            </div>
          </div>

          {/* Section 6: Graph Studio Controls & Sliders */}
          <div className="space-y-3 pt-2 border-t border-[#1A2233]">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#2FD9C4] uppercase tracking-wider">
              <Sliders className="w-3.5 h-3.5" />
              <span>🎛️ Force Field & Simulation Parameters</span>
            </div>

            <div className="p-3 rounded-xl bg-[#111726] border border-[#212B41] space-y-3 text-xs">
              <div>
                <div className="flex justify-between text-[#9AA3BC] mb-1">
                  <span>Coulomb Repulsion</span>
                  <span id="valParamRepel" className="font-mono text-[#2FD9C4] font-semibold">
                    {coulombRepulsion}
                  </span>
                </div>
                <input
                  id="paramRepelRange"
                  type="range"
                  min="1000"
                  max="12000"
                  step="200"
                  value={coulombRepulsion}
                  onChange={(e) => setCoulombRepulsion(Number(e.target.value))}
                  className="w-full accent-[#2FD9C4]"
                />
              </div>

              <div>
                <div className="flex justify-between text-[#9AA3BC] mb-1">
                  <span>Spring Tension</span>
                  <span id="valParamSpring" className="font-mono text-[#2FD9C4] font-semibold">
                    {springTension}
                  </span>
                </div>
                <input
                  id="paramSpringRange"
                  type="range"
                  min="0.01"
                  max="0.12"
                  step="0.005"
                  value={springTension}
                  onChange={(e) => setSpringTension(Number(e.target.value))}
                  className="w-full accent-[#2FD9C4]"
                />
              </div>

              <div>
                <div className="flex justify-between text-[#9AA3BC] mb-1">
                  <span>Similarity Linking Threshold</span>
                  <span id="valParamSim" className="font-mono text-[#2FD9C4] font-semibold">
                    {similarityThreshold}
                  </span>
                </div>
                <input
                  id="paramSimRange"
                  type="range"
                  min="0.40"
                  max="0.95"
                  step="0.05"
                  value={similarityThreshold}
                  onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                  className="w-full accent-[#2FD9C4]"
                />
              </div>
            </div>

            {/* Quick Actions Grid */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                id="exportBtn"
                onClick={handleExportJson}
                className="p-2.5 rounded-xl bg-[#111726] hover:bg-[#151C2E] border border-[#212B41] text-[#E9ECF6] flex items-center gap-2 font-medium"
              >
                <Download className="w-4 h-4 text-[#38BDF8]" />
                <span>Export Graph</span>
              </button>
              <button
                id="menuOpenClassifierBtn"
                onClick={() => openModal('classifierModal')}
                className="p-2.5 rounded-xl bg-[#111726] hover:bg-[#151C2E] border border-[#212B41] text-[#E9ECF6] flex items-center gap-2 font-medium"
              >
                <FileText className="w-4 h-4 text-[#2FD9C4]" />
                <span>Classifier Studio</span>
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
