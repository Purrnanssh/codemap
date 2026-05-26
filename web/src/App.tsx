import { useEffect, useState, useMemo } from 'react';
import { GraphViewer } from './components/graph/GraphViewer';
import { Sidebar } from './components/panels/Sidebar';
import { InspectorPanel } from './components/panels/InspectorPanel';
import { GraphLegend } from './components/panels/GraphLegend';
import type { CodeMapGraph, CodeMapNode, Hotspot, GraphMode } from './types/codemap';
import { buildModuleGraph, enhanceGraph } from './utils/graphMetrics';
import { Layers } from 'lucide-react';

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
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-primary animate-pulse text-xl font-light tracking-wide">Loading CodeMap Data...</div>
      </div>
    );
  }

  if (!activeData) return null;

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-background text-foreground cinematic-bg">
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 glass-panel px-1.5 py-1.5 rounded-full flex gap-1">
        <button 
          onClick={() => { setGraphMode('symbol'); setSelectedNode(null); }}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${graphMode === 'symbol' ? 'bg-primary text-white shadow-lg' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
        >
          Symbol View
        </button>
        <button 
          onClick={() => { setGraphMode('module'); setSelectedNode(null); }}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all flex items-center gap-2 ${graphMode === 'module' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
        >
          <Layers className="w-4 h-4" />
          Module View
        </button>
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
    </div>
  );
}

export default App;
