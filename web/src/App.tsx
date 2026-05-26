import { useEffect, useState, useMemo } from 'react';
import { GraphViewer } from './components/graph/GraphViewer';
import { Sidebar } from './components/panels/Sidebar';
import { InspectorPanel } from './components/panels/InspectorPanel';
import { GraphLegend } from './components/panels/GraphLegend';
import type { CodeMapGraph, CodeMapNode, Hotspot, GraphMode } from './types/codemap';
import { buildModuleGraph, enhanceGraph } from './utils/graphMetrics';
import { Layers } from 'lucide-react';
import { motion } from 'framer-motion';

function App() {
  const [rawData, setRawData] = useState<{ symbol: CodeMapGraph, module: CodeMapGraph } | null>(null);
  const [graphMode, setGraphMode] = useState<GraphMode>('symbol');
  const [selectedNode, setSelectedNode] = useState<CodeMapNode | null>(null);
  const [hoverNode, setHoverNode] = useState<CodeMapNode | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/data.json')
      .then(res => res.json())
      .then((json: CodeMapGraph) => {
        const symbolGraph = json;
        const moduleGraph = buildModuleGraph(json);
        
        setRawData({
          symbol: enhanceGraph(symbolGraph),
          module: enhanceGraph(moduleGraph)
        });
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load graph data:", err);
        setLoading(false);
      });
  }, []);

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

  if (loading) {
    return (
      <div className="min-h-screen bg-background cinematic-bg flex flex-col items-center justify-center">
        <motion.div 
          animate={{ scale: [0.95, 1, 0.95], opacity: [0.5, 1, 0.5] }} 
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
          className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 shadow-[0_0_30px_rgba(255,255,255,0.05)] flex items-center justify-center mb-4"
        >
          <div className="w-3 h-3 rounded-full bg-slate-300" />
        </motion.div>
        <div className="text-slate-500 text-[10px] tracking-widest uppercase font-medium">Initializing Workspace</div>
      </div>
    );
  }

  if (!activeData) return null;

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
