import { useState, useCallback, useEffect } from 'react';
import { ReactFlow, Controls, Background, useNodesState, useEdgesState, MarkerType } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { Loader2, Search, X } from 'lucide-react';
import { codemapApi } from './api/client';

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: any[], edges: any[], direction = 'LR') => {
  dagreGraph.setGraph({ rankdir: direction, nodesep: 30, ranksep: 150 });

  nodes.forEach((node) => {
    // Arbitrary size for the layout algorithm
    dagreGraph.setNode(node.id, { width: 180, height: 40 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: 'left',
      sourcePosition: 'right',
      position: {
        x: nodeWithPosition.x - 90,
        y: nodeWithPosition.y - 20,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export default function App() {
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState<'idle' | 'polling' | 'completed' | 'failed'>('idle');
  const [jobId, setJobId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [statusText, setStatusText] = useState('Connecting...');
  
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);
  const [selectedNodeData, setSelectedNodeData] = useState<any | null>(null);

  useEffect(() => {
    if (status !== 'polling' || !jobId) return;
    
    const interval = setInterval(async () => {
      try {
        const job = await codemapApi.pollJobStatus(jobId);
        if (job.status === 'cloning') setStatusText('Cloning repository...');
        if (job.status === 'extracting') setStatusText('Extracting syntax trees...');
        if (job.status === 'building') setStatusText('Synthesizing graph...');
        
        if (job.status === 'completed') {
          clearInterval(interval);
          const rawGraph = await codemapApi.getGraph(jobId);
          
          const rawNodes = rawGraph.nodes.map((n: any) => ({
            id: n.id,
            data: { label: n.name || n.id, raw: n },
            style: { 
              background: '#1e293b', 
              color: '#f8fafc', 
              border: '1px solid #334155',
              borderRadius: '8px',
              padding: '10px',
              fontSize: '12px'
            }
          }));
          
          const rawEdges = rawGraph.edges.map((e: any, i: number) => {
             const source = typeof e.source === 'string' ? e.source : e.source.id;
             const target = typeof e.target === 'string' ? e.target : e.target.id;
             return {
               id: `e${i}-${source}-${target}`,
               source,
               target,
               animated: true,
               style: { stroke: '#475569' },
               markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' }
             };
          });

          const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rawNodes, rawEdges);
          setNodes(layoutedNodes);
          setEdges(layoutedEdges);
          setStatus('completed');
        } else if (job.status === 'failed') {
          clearInterval(interval);
          setStatus('failed');
          setErrorMsg(job.error_msg || 'Unknown error occurred.');
        }
      } catch (err: any) {
        clearInterval(interval);
        setStatus('failed');
        setErrorMsg(err.message);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [status, jobId, setNodes, setEdges]);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setStatus('polling');
    setErrorMsg(null);
    setSelectedNodeData(null);
    try {
      const id = await codemapApi.ingestWorkspace(url);
      setJobId(id);
    } catch (err: any) {
      setStatus('failed');
      setErrorMsg(err.message);
    }
  };

  const onNodeClick = useCallback((_: any, node: any) => {
    setSelectedNodeData(node.data.raw);
  }, []);

  return (
    <div className="w-screen h-screen bg-slate-950 text-slate-200 font-sans overflow-hidden">
      {/* Navbar / Header */}
      <div className="absolute top-0 left-0 w-full p-4 z-10 flex gap-4 items-center bg-slate-950/80 backdrop-blur border-b border-slate-800">
        <h1 className="text-xl font-bold text-white tracking-tight shrink-0">CodeMap</h1>
        <form onSubmit={handleAnalyze} className="flex gap-2 w-full max-w-2xl">
          <input
            type="text"
            placeholder="https://github.com/encode/starlette"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={status === 'polling'}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!url.trim() || status === 'polling'}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 disabled:opacity-50 transition-colors"
          >
            {status === 'polling' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Analyze
          </button>
        </form>
        {status === 'polling' && <span className="text-sm text-blue-400 animate-pulse">{statusText}</span>}
        {status === 'failed' && <span className="text-sm text-red-400">{errorMsg}</span>}
      </div>

      {/* Main Graph Area */}
      <div className="w-full h-full pt-16">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
          colorMode="dark"
          minZoom={0.1}
        >
          <Background color="#334155" gap={16} />
          <Controls className="!bg-slate-900 !border-slate-800 !fill-slate-300" />
        </ReactFlow>
      </div>

      {/* Node Inspector Sidebar */}
      {selectedNodeData && (
        <div className="absolute top-20 right-4 w-80 bg-slate-900/90 backdrop-blur-xl border border-slate-700 rounded-xl shadow-2xl p-4 z-20 flex flex-col max-h-[calc(100vh-100px)] overflow-hidden">
          <div className="flex justify-between items-start mb-4 shrink-0">
            <h2 className="text-lg font-bold text-white break-all pr-4">{selectedNodeData.name || selectedNodeData.id}</h2>
            <button onClick={() => setSelectedNodeData(null)} className="p-1 hover:bg-slate-800 rounded">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="overflow-y-auto space-y-4 text-sm flex-1">
            <div>
              <span className="text-slate-400 text-xs uppercase font-bold tracking-wider">Module</span>
              <p className="mt-1 font-mono text-slate-300 break-all">{selectedNodeData.module || 'Unknown'}</p>
            </div>
            {selectedNodeData.complexity !== undefined && (
              <div>
                <span className="text-slate-400 text-xs uppercase font-bold tracking-wider">Complexity</span>
                <p className="mt-1 font-mono text-slate-300">{selectedNodeData.complexity}</p>
              </div>
            )}
            <div>
              <span className="text-slate-400 text-xs uppercase font-bold tracking-wider">Kind</span>
              <p className="mt-1 font-mono text-slate-300">{selectedNodeData.kind || 'Unknown'}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
