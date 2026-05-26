import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { CodeMapGraph, CodeMapNode, CodeMapEdge } from '../../types/codemap';
import { getComplexityColor, EDGE_COLORS } from '../../utils/colors';

interface GraphViewerProps {
  data: CodeMapGraph;
  onNodeClick: (node: CodeMapNode) => void;
  onNodeHover: (node: CodeMapNode | null) => void;
  selectedNode: CodeMapNode | null;
  hoverNode: CodeMapNode | null;
}

export const GraphViewer: React.FC<GraphViewerProps> = ({ data, onNodeClick, onNodeHover, selectedNode, hoverNode }) => {
  const fgRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: window.innerWidth, height: window.innerHeight });

  // Pre-calculate neighbor map for fast lookup on hover
  const neighbors = useMemo(() => {
    const map = new Map<string, Set<string>>();
    data.edges.forEach((edge: any) => {
      const s = typeof edge.source === 'object' ? edge.source.id : edge.source;
      const t = typeof edge.target === 'object' ? edge.target.id : edge.target;
      if (!map.has(s)) map.set(s, new Set());
      if (!map.has(t)) map.set(t, new Set());
      map.get(s)!.add(t);
      map.get(t)!.add(s);
    });
    return map;
  }, [data]);

  // Memoize graphData to prevent React from passing new object references on every render
  const graphData = useMemo(() => ({ nodes: data.nodes, links: data.edges }), [data]);

  useEffect(() => {
    const handleResize = () => setDimensions({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Center on selected node with cinematic ease
  useEffect(() => {
    if (selectedNode && fgRef.current) {
      // Lookup the exact live node instance inside the physics simulation
      // This prevents using stale x/y coordinates from frozen React references
      const simNode = fgRef.current.graphData().nodes.find((n: any) => n.id === selectedNode.id);
      
      if (simNode && simNode.x !== undefined && simNode.y !== undefined) {
        // Snappier transition (800ms) and tighter zoom for focus
        fgRef.current.centerAt(simNode.x, simNode.y, 800);
        fgRef.current.zoom(3.5, 800);
      }
    }
  }, [selectedNode, data]);

  // Adjust physics for denser graphs
  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force('charge').strength(-350); // increased repulsion for breathing room
      fgRef.current.d3Force('collide', (d: any) => d.val * 1.5 + 8); // larger collision radius
    }
  }, [data]);

  const paintNode = useCallback((node: CodeMapNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const isSelected = selectedNode?.id === node.id;
    const isHovered = hoverNode?.id === node.id;
    const isNeighbor = (hoverNode && neighbors.get(hoverNode.id)?.has(node.id)) || (selectedNode && neighbors.get(selectedNode.id)?.has(node.id));
    
    // Dimming logic
    const hasFocus = hoverNode || selectedNode;
    const isDimmed = hasFocus && !isHovered && !isSelected && !isNeighbor;
    
    // Scale node subtly if active
    const scaleFactor = (isSelected || isHovered) ? 1.3 : 1;
    const size = (node.val || 2) * scaleFactor;
    const color = getComplexityColor(node.complexity);

    ctx.beginPath();
    ctx.arc(node.x!, node.y!, size, 0, 2 * Math.PI, false);
    // Blend dimmed nodes deeply into the slate-900 background
    ctx.fillStyle = isDimmed ? 'rgba(30, 41, 59, 0.3)' : color;

    // Elegant inner glow for focused nodes
    if ((node.isInCycle && !isDimmed) || isHovered || isSelected) {
      ctx.shadowBlur = (isHovered || isSelected) ? 25 : 15;
      ctx.shadowColor = (isHovered || isSelected) ? color : '#ef4444';
    } else {
      ctx.shadowBlur = 0;
    }

    ctx.fill();
    ctx.shadowBlur = 0; // Reset

    // Cinematic focus ring
    if (isSelected || isHovered) {
      ctx.beginPath();
      ctx.arc(node.x!, node.y!, size + (5 / globalScale), 0, 2 * Math.PI, false);
      ctx.lineWidth = 1.5 / globalScale;
      ctx.strokeStyle = isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.4)';
      ctx.stroke();
    } else if (!isDimmed && (node.kind === 'external' || node.kind === 'unresolved')) {
      ctx.beginPath();
      ctx.arc(node.x!, node.y!, size, 0, 2 * Math.PI, false);
      ctx.lineWidth = 0.5 / globalScale;
      ctx.strokeStyle = '#444444';
      ctx.setLineDash([1 / globalScale, 1 / globalScale]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Progressive Disclosure: Labels
    if (!isDimmed && (globalScale > 3 || isSelected || isHovered || isNeighbor)) {
      const label = node.name || node.id;
      const fontSize = Math.max(12 / globalScale, 1.5);
      
      // Enhance text contrast for focused elements
      ctx.font = `${isHovered || isSelected ? '500' : '400'} ${fontSize}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = isHovered || isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.55)';
      
      // Text drop shadow to ensure legibility over lines
      ctx.shadowColor = '#0f172a';
      ctx.shadowBlur = 4 / globalScale;
      ctx.fillText(label, node.x!, node.y! + size + fontSize + (3 / globalScale));
      ctx.shadowBlur = 0;
    }
  }, [selectedNode, hoverNode, neighbors]);

  return (
    <div className={`absolute inset-0 bg-transparent overflow-hidden ${hoverNode ? 'cursor-pointer' : 'cursor-grab active:cursor-grabbing'}`}>
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        nodeId="id"
        width={dimensions.width}
        height={dimensions.height}
        nodeLabel={() => ''} // disable default title tooltip for cleaner UI
        nodeVal="val"
        nodeCanvasObject={paintNode as any}
        onNodeHover={(n) => {
          if (hoverNode?.id !== (n as CodeMapNode | null)?.id) {
            onNodeHover(n as CodeMapNode | null);
          }
        }}
        onNodeClick={(n) => onNodeClick(n as CodeMapNode)}
        
        // Dynamic edge rendering
        linkColor={(link: any) => {
          const edge = link as CodeMapEdge;
          const sId = typeof edge.source === 'object' ? (edge.source as CodeMapNode).id : edge.source;
          const tId = typeof edge.target === 'object' ? (edge.target as CodeMapNode).id : edge.target;
          
          const hasFocus = hoverNode || selectedNode;
          const isConnectedToFocus = hasFocus && 
            (sId === hoverNode?.id || tId === hoverNode?.id || sId === selectedNode?.id || tId === selectedNode?.id);
          
          if (hasFocus && !isConnectedToFocus) return 'rgba(30, 41, 59, 0.2)'; // fade out unrelated edges
          if (edge.isInCycle) return '#ef4444'; // Bright red for cycle edges
          if (isConnectedToFocus) return 'rgba(255, 255, 255, 0.6)'; // bright white-ish for connected active edges
          return EDGE_COLORS[edge.kind] || EDGE_COLORS.internal;
        }}
        linkWidth={(link: any) => {
          const edge = link as CodeMapEdge;
          const sId = typeof edge.source === 'object' ? (edge.source as CodeMapNode).id : edge.source;
          const tId = typeof edge.target === 'object' ? (edge.target as CodeMapNode).id : edge.target;
          
          const hasFocus = hoverNode || selectedNode;
          const isConnectedToFocus = hasFocus && 
            (sId === hoverNode?.id || tId === hoverNode?.id || sId === selectedNode?.id || tId === selectedNode?.id);
          
          if (isConnectedToFocus) return 2;
          if (hasFocus && !isConnectedToFocus) return 0.2;
          return edge.isInCycle ? 2 : (edge.kind === 'internal' ? 1 : 0.5);
        }}
        linkLineDash={(link: any) => (link.kind === 'external' || link.kind === 'unresolved') && !link.isInCycle ? [2, 2] : null}
        
        // Choreographed energy pulses
        linkDirectionalParticles={(link: any) => {
          const sId = typeof link.source === 'object' ? link.source.id : link.source;
          const tId = typeof link.target === 'object' ? link.target.id : link.target;
          
          const hasFocus = hoverNode || selectedNode;
          const isConnectedToFocus = hasFocus && 
            (sId === hoverNode?.id || tId === hoverNode?.id || sId === selectedNode?.id || tId === selectedNode?.id);

          if (link.isInCycle) return 5;
          if (hasFocus) {
            return isConnectedToFocus ? 4 : 0; // dense particles on active, zero on dimmed
          }
          return (link.kind === 'internal' || link.kind === 'self') ? 1 : 0;
        }}
        linkDirectionalParticleWidth={(link: any) => link.isInCycle ? 3 : 2}
        linkDirectionalParticleSpeed={(link: any) => link.isInCycle ? 0.012 : 0.006}
        linkDirectionalParticleColor={(link: any) => link.isInCycle ? 'rgba(239, 68, 68, 0.9)' : 'rgba(255, 255, 255, 0.8)'}
        
        // Physics tuning
        d3VelocityDecay={0.12} // Lower decay creates a smoother, more fluid settling inertia
        warmupTicks={150} // Pre-compute more frames for instant stability on load
        cooldownTicks={100}
      />
    </div>
  );
};
