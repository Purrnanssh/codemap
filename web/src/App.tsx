import { useEffect, useState, useMemo } from 'react';
import { GraphViewer } from './components/graph/GraphViewer';
import { Sidebar } from './components/panels/Sidebar';
import { InspectorPanel } from './components/panels/InspectorPanel';
import { GraphLegend } from './components/panels/GraphLegend';
import type { CodeMapGraph, CodeMapNode, Hotspot, GraphMode } from './types/codemap';
import { buildModuleGraph, enhanceGraph } from './utils/graphMetrics';
import { Layers, FolderCode, ArrowRight, Loader2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { codemapApi, type JobStatus } from './api/client';

function App() {
  const [rawData, setRawData] = useState<{ symbol: CodeMapGraph, module: CodeMapGraph } | null>(null);
  const [graphMode, setGraphMode] = useState<GraphMode>('symbol');
  const [selectedNode, setSelectedNode] = useState<CodeMapNode | null>(null);
  const [hoverNode, setHoverNode] = useState<CodeMapNode | null>(null);
  
  // Ingestion State
  const [workspacePath, setWorkspacePath] = useState('');
  const [ingestStatus, setIngestStatus] = useState<'idle' | 'queued' | 'cloning' | 'extracting' | 'building' | 'completed' | 'failed'>('idle');
  const [jobId, setJobId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Polling Effect
  useEffect(() => {
    if (!jobId || ingestStatus === 'completed' || ingestStatus === 'failed') return;

    const interval = setInterval(async () => {
      try {
        const status: JobStatus = await codemapApi.pollJobStatus(jobId);
        setIngestStatus(status.status);
        
        if (status.status === 'completed') {
          const json = await codemapApi.getGraph(jobId);
          setRawData({
            symbol: enhanceGraph(json),
            module: enhanceGraph(buildModuleGraph(json))
          });
        } else if (status.status === 'failed') {
          setErrorMsg(status.error_msg || "Unknown ingestion error");
        }
      } catch (err: any) {
        setIngestStatus('failed');
        setErrorMsg(err.message);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [jobId, ingestStatus]);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspacePath.trim()) return;
    
    setIngestStatus('queued');
    setErrorMsg(null);
    try {
      const id = await codemapApi.ingestWorkspace(workspacePath);
      setJobId(id);
    } catch (err: any) {
      setIngestStatus('failed');
      setErrorMsg(err.message);
    }
  };

  const activeData = rawData ? rawData[graphMode] : null;

  const hotspots = useMemo(() => {
    if (!activeData) return [];
    
    const fanInMap: Record<string, number> = {};
    activeData.edges.forEach((edge: any) => {
      const target = typeof edge.target === 'object' ? edge.target.id : edge.target;
      fanInMap[target] = (fanInMap[target] || 0) + 1;
    });

    const candidates: Hotspot[] = activeData.nodes
      .filter((n: any) => n.kind === 'function')
      .map((node: any) => {
        const fanIn = fanInMap[node.id] || 0;
        const cx = node.complexity || 1;
        return {
          id: node.id,
          name: node.name || node.id.split('.').pop() || '',
          complexity: cx,
          fanIn,
          score: cx * fanIn,
          node
        };
      })
      .filter((h: any) => h.score > 0);

    return candidates.sort((a, b) => b.score - a.score).slice(0, 50);
  }, [activeData]);

  if (!activeData) {
    const isProcessing = ['queued', 'cloning', 'extracting', 'building'].includes(ingestStatus);
    
    let statusText = 'Connecting to engine...';
    if (ingestStatus === 'cloning') statusText = 'Cloning repository...';
    if (ingestStatus === 'extracting') statusText = 'Extracting abstract syntax trees...';
    if (ingestStatus === 'building') statusText = 'Synthesizing topologies...';

    return (
      <div className="min-h-screen bg-background cinematic-bg flex flex-col items-center justify-center p-6 relative">
        {/* Subtle background pulse when processing */}
        <AnimatePresence>
          {isProcessing && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-0 overflow-hidden pointer-events-none"
            >
              <motion.div 
                animate={{ scale: [1, 1.05, 1], opacity: [0.1, 0.2, 0.1] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-white/5 blur-[120px] rounded-full"
              />
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md w-full relative z-10"
        >
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 shadow-[0_0_30px_rgba(255,255,255,0.05)] flex items-center justify-center mx-auto mb-6">
              <FolderCode className="w-8 h-8 text-slate-300" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight mb-2">Initialize Workspace</h1>
            <p className="text-slate-400 text-sm font-medium">Paste a GitHub URL or absolute local path to begin.</p>
          </div>

          <form onSubmit={handleIngest} className="space-y-4">
            <div className="relative group">
              <input 
                type="text" 
                value={workspacePath}
                onChange={(e) => setWorkspacePath(e.target.value)}
                placeholder="https://github.com/encode/starlette"
                disabled={isProcessing}
                className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-white/30 transition-all disabled:opacity-50"
              />
            </div>
            
            <button 
              type="submit"
              disabled={!workspacePath.trim() || isProcessing}
              className="relative w-full overflow-hidden bg-white text-black font-medium text-sm rounded-xl px-4 py-3 flex items-center justify-center gap-2 hover:bg-slate-200 transition-colors disabled:opacity-80 disabled:cursor-wait h-[44px]"
            >
              <AnimatePresence mode="wait">
                {isProcessing ? (
                  <motion.div
                    key="processing"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                    className="flex items-center gap-2"
                  >
                    <Loader2 className="w-4 h-4 animate-spin opacity-50" />
                    <span>{statusText}</span>
                  </motion.div>
                ) : (
                  <motion.div
                    key="idle"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                    className="flex items-center gap-2"
                  >
                    Scan Repository <ArrowRight className="w-4 h-4 opacity-50" />
                  </motion.div>
                )}
              </AnimatePresence>
            </button>
          </form>

          <AnimatePresence>
            {errorMsg && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex gap-3 overflow-hidden"
              >
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 opacity-80" />
                <p className="leading-relaxed font-medium">{errorMsg}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    );
  }

  return (
    <motion.div 
      initial={{ opacity: 0 }} 
      animate={{ opacity: 1 }} 
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="relative w-screen h-screen overflow-hidden bg-background text-foreground cinematic-bg"
    >
      <div className="absolute top-6 left-1/2 -translate-x-1/2 z-20 p-1 rounded-full flex gap-1 bg-slate-900/60 border border-white/10 shadow-2xl backdrop-blur-xl">
        {(['symbol', 'module'] as GraphMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => { setGraphMode(mode); setSelectedNode(null); }}
            className={`relative px-5 py-1.5 rounded-full text-xs tracking-wide font-medium transition-colors duration-200 flex items-center gap-2 ${
              graphMode === mode ? 'text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {graphMode === mode && (
              <motion.div
                layoutId="activeTab"
                className="absolute inset-0 bg-white/10 border border-white/5 rounded-full"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative z-10 flex items-center gap-1.5 capitalize">
              {mode === 'module' && <Layers className="w-3.5 h-3.5" />}
              {mode} View
            </span>
          </button>
        ))}
      </div>

      <GraphViewer 
        key={graphMode}
        data={activeData} 
        selectedNode={selectedNode}
        hoverNode={hoverNode}
        onNodeClick={setSelectedNode}
        onNodeHover={(n) => setHoverNode(n || null)} 
      />
      
      <Sidebar 
        hotspots={hotspots}
        selectedId={selectedNode?.id || null}
        onHotspotClick={(h) => setSelectedNode(h.node)}
      />

      <InspectorPanel 
        node={selectedNode}
        edges={activeData.edges}
        onClose={() => setSelectedNode(null)}
      />

      <GraphLegend isInspectorOpen={!!selectedNode} />
    </motion.div>
  );
}

export default App;
