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

  useEffect(() => {
    const handleResize = () => setDimensions({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Center on selected node
  useEffect(() => {
    if (selectedNode && selectedNode.x !== undefined && selectedNode.y !== undefined && fgRef.current) {
      fgRef.current.centerAt(selectedNode.x, selectedNode.y, 1000);
      fgRef.current.zoom(3, 1000);
    }
  }, [selectedNode]);

  // Adjust physics for denser graphs
  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force('charge').strength(-300); // more repulsion
      fgRef.current.d3Force('collide', (d: any) => d.val * 1.5 + 5);
    }
  }, [data]);

  const paintNode = useCallback((node: CodeMapNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const isSelected = selectedNode?.id === node.id;
    const isHovered = hoverNode?.id === node.id;
    const isNeighbor = hoverNode && neighbors.get(hoverNode.id)?.has(node.id);
    
    // Dimming logic
    const isDimmed = hoverNode && !isHovered && !isNeighbor;
    
    const size = node.val || 2;
    const color = getComplexityColor(node.complexity);

    ctx.beginPath();
    ctx.arc(node.x!, node.y!, size, 0, 2 * Math.PI, false);
    ctx.fillStyle = isDimmed ? 'rgba(100, 100, 100, 0.1)' : color;

    // Glowing logic for cycles or hovered
    if ((node.isInCycle && !isDimmed) || isHovered) {
      ctx.shadowBlur = isHovered ? 15 : 20;
      ctx.shadowColor = isHovered ? '#ffffff' : '#ef4444'; // Red glow for cycles
    } else {
      ctx.shadowBlur = 0;
    }

    ctx.fill();
    ctx.shadowBlur = 0; // Reset

    if (isSelected || isHovered) {
      ctx.lineWidth = 1.5 / globalScale;
      ctx.strokeStyle = '#ffffff';
      ctx.stroke();
    } else if (!isDimmed && (node.kind === 'external' || node.kind === 'unresolved')) {
      ctx.lineWidth = 0.5 / globalScale;
      ctx.strokeStyle = '#444444';
      ctx.setLineDash([1 / globalScale, 1 / globalScale]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Progressive Disclosure: Labels only if zoomed in, hovered, or selected
    if (!isDimmed && (globalScale > 3 || isSelected || isHovered || isNeighbor)) {
      const label = node.name || node.id;
      const fontSize = Math.max(12 / globalScale, 1.5);
      ctx.font = `${fontSize}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = isHovered || isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.7)';
      ctx.fillText(label, node.x!, node.y! + size + fontSize);
    }
  }, [selectedNode, hoverNode, neighbors]);

  return (
    <div className="absolute inset-0 bg-transparent overflow-hidden cursor-move">
      <ForceGraph2D
        ref={fgRef}
        graphData={{ nodes: data.nodes, links: data.edges }}
        width={dimensions.width}
        height={dimensions.height}
        nodeLabel={(n: any) => n.id}
        nodeVal="val"
        nodeCanvasObject={paintNode as any}
        onNodeHover={(n) => onNodeHover(n as CodeMapNode | null)}
        onNodeClick={(n) => onNodeClick(n as CodeMapNode)}
        
        // Edge styling
        linkColor={(link: any) => {
          const edge = link as CodeMapEdge;
          const sId = typeof edge.source === 'object' ? (edge.source as CodeMapNode).id : edge.source;
          const tId = typeof edge.target === 'object' ? (edge.target as CodeMapNode).id : edge.target;
          const isDimmed = hoverNode && hoverNode.id !== sId && hoverNode.id !== tId;
          
          if (isDimmed) return 'rgba(100, 100, 100, 0.05)';
          if (edge.isInCycle) return '#ef4444'; // Bright red for cycle edges
          return EDGE_COLORS[edge.kind] || EDGE_COLORS.internal;
        }}
        linkWidth={(link: any) => {
          const edge = link as CodeMapEdge;
          if (hoverNode) {
            const sId = typeof edge.source === 'object' ? (edge.source as CodeMapNode).id : edge.source;
            const tId = typeof edge.target === 'object' ? (edge.target as CodeMapNode).id : edge.target;
            if (hoverNode.id === sId || hoverNode.id === tId) return 2;
          }
          return edge.isInCycle ? 2 : (edge.kind === 'internal' ? 1 : 0.5);
        }}
        linkLineDash={(link: any) => (link.kind === 'external' || link.kind === 'unresolved') && !link.isInCycle ? [2, 2] : null}
        
        // Energy pulse animations
        linkDirectionalParticles={(link: any) => {
          if (link.isInCycle) return 5;
          if (hoverNode) {
            const sId = typeof link.source === 'object' ? link.source.id : link.source;
            const tId = typeof link.target === 'object' ? link.target.id : link.target;
            if (hoverNode.id === sId || hoverNode.id === tId) return 3;
            return 0; // Dimmed edges have no particles to save performance
          }
          // Default baseline energy
          return (link.kind === 'internal' || link.kind === 'self') ? 2 : 1;
        }}
        linkDirectionalParticleWidth={(link: any) => link.isInCycle ? 3 : 2}
        linkDirectionalParticleSpeed={(link: any) => link.isInCycle ? 0.015 : 0.008}
        linkDirectionalParticleColor={(link: any) => link.isInCycle ? 'rgba(239, 68, 68, 0.9)' : 'rgba(255, 255, 255, 0.6)'}
        
        d3VelocityDecay={0.2}
        warmupTicks={50}
        cooldownTicks={100}
      />
    </div>
  );
};
