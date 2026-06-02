import { useEffect, useState, useMemo, useRef } from 'react';
import { GraphViewer } from './components/graph/GraphViewer';
import { Sidebar } from './components/panels/Sidebar';
import { InspectorPanel } from './components/panels/InspectorPanel';
import { GraphLegend } from './components/panels/GraphLegend';
import { RepositoryCard } from './components/panels/RepositoryCard';
import { EmptyStateCard, ErrorStateCard } from './components/panels/StateCards';
import type { CodeMapGraph, CodeMapNode, Hotspot, GraphMode } from './types/codemap';
import { buildModuleGraph, enhanceGraph } from './utils/graphMetrics';
import { Layers, FolderCode, ArrowRight, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { codemapApi, type JobStatus } from './api/client';

function App() {
  const [rawData, setRawData] = useState<{ symbol: CodeMapGraph, module: CodeMapGraph } | null>(null);
  const [graphMode, setGraphMode] = useState<GraphMode>('symbol');
  const [selectedNode, setSelectedNode] = useState<CodeMapNode | null>(null);
  const [hoverNode, setHoverNode] = useState<CodeMapNode | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  
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

  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is already typing in an input or textarea
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === '/') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const resetWorkspace = () => {
    setRawData(null);
    setIngestStatus('idle');
    setJobId(null);
    setErrorMsg(null);
    setWorkspacePath('');
  };

  if (errorMsg && ingestStatus === 'failed') {
    return <ErrorStateCard errorMsg={errorMsg} onReset={resetWorkspace} />;
  }

  if (activeData && activeData.nodes.length === 0) {
    return <EmptyStateCard summary={rawData?.symbol.summary} onReset={resetWorkspace} />;
  }

  if (!activeData) {
    const isProcessing = ['queued', 'cloning', 'extracting', 'building', 'completed'].includes(ingestStatus);
    
    let statusText = 'Connecting to engine...';
    if (ingestStatus === 'cloning') statusText = 'Cloning repository...';
    if (ingestStatus === 'extracting') statusText = 'Extracting abstract syntax trees...';
    if (ingestStatus === 'building') statusText = 'Synthesizing topologies...';
    if (ingestStatus === 'completed') statusText = 'Loading graph topology...';

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
            <h1 className="text-5xl md:text-6xl font-bold tracking-tight text-white drop-shadow-md">
              CodeMap
            </h1>
            <p className="text-slate-400 text-lg max-w-md tracking-wide">
              Visualize the architecture of any repository
            </p>
          </div>

          <form onSubmit={handleIngest} className="space-y-4">
            <div className="relative group">
              <input 
                ref={inputRef}
                type="text" 
                value={workspacePath}
                onChange={(e) => setWorkspacePath(e.target.value)}
                placeholder="https://github.com/encode/starlette"
                disabled={isProcessing}
                className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-white/30 transition-all disabled:opacity-50 pr-12"
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none opacity-50">
                <kbd className="hidden sm:inline-block px-2 py-0.5 text-xs font-mono font-semibold bg-white/10 border border-white/20 rounded text-slate-300 shadow-sm">
                  /
                </kbd>
              </div>
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
        </motion.div>
        
        {/* Creator Credit / Signature */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 1 }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 flex items-center gap-2 text-[13px] text-white/50 tracking-wide font-medium z-10"
        >
          <span>Built by Purrnanssh Sinha</span>
          <div className="w-1 h-1 rounded-full bg-white/30" />
          <a 
            href="https://github.com/Purrnanssh" 
            target="_blank" 
            rel="noopener noreferrer"
            className="hover:text-white hover:drop-shadow-[0_0_8px_rgba(255,255,255,0.6)] transition-all duration-300"
            title="View on GitHub"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
          </a>
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
      <div className="absolute top-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center">

        <div className="p-1 rounded-full flex gap-1 bg-slate-900/60 border border-white/10 shadow-2xl backdrop-blur-xl">
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
      </div>

      <GraphViewer 
        key={graphMode}
        data={activeData} 
        selectedNode={selectedNode}
        hoverNode={hoverNode}
        onNodeClick={setSelectedNode}
        onNodeHover={(n) => setHoverNode(n || null)} 
        isSidebarOpen={isSidebarOpen}
      />
      
      <Sidebar 
        hotspots={hotspots}
        selectedId={selectedNode?.id || null}
        onHotspotClick={(h) => setSelectedNode(h.node)}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      <InspectorPanel 
        node={selectedNode}
        edges={activeData.edges}
        onClose={() => setSelectedNode(null)}
      />

      <GraphLegend isInspectorOpen={!!selectedNode} />

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 pointer-events-auto">
        <RepositoryCard workspacePath={workspacePath} />
      </div>
    </motion.div>
  );
}

export default App;
