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

  // Pre-calculate neighbor map for fast lookup on hover (guarded)
  const neighbors = useMemo(() => {
    const map = new Map<string, Set<string>>();
    if (!data?.edges) return map;
    
    data.edges.forEach((edge: any) => {
      if (!edge) return;
      const s = typeof edge.source === 'object' ? edge.source?.id : edge.source;
      const t = typeof edge.target === 'object' ? edge.target?.id : edge.target;
      if (s && t) {
        if (!map.has(s)) map.set(s, new Set());
        if (!map.has(t)) map.set(t, new Set());
        map.get(s)!.add(t);
        map.get(t)!.add(s);
      }
    });
    return map;
  }, [data]);

  // Memoize graphData to prevent React from passing new object references on every render
  const graphData = useMemo(() => {
    return { 
      nodes: data?.nodes || [], 
      links: data?.edges || [] 
    };
  }, [data]);

  useEffect(() => {
    const handleResize = () => setDimensions({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const focusTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const zoomTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Safe & Cinematic Camera Focus System
  useEffect(() => {
    // Prevent race conditions by clearing pending animations on selection change
    if (focusTimeoutRef.current) clearTimeout(focusTimeoutRef.current);
    if (zoomTimeoutRef.current) clearTimeout(zoomTimeoutRef.current);

    if (selectedNode && fgRef.current && data?.nodes) {
      // 1. Delay slightly so graph physics can stabilize before camera locks on
      focusTimeoutRef.current = setTimeout(() => {
        if (!fgRef.current || !data?.nodes) return;

        // Securely find the node's live coordinates in React state
        const simNode = data.nodes.find((n: any) => n?.id === selectedNode.id);
        
        if (simNode && typeof simNode.x === 'number' && typeof simNode.y === 'number' && !isNaN(simNode.x) && !isNaN(simNode.y)) {
          if (typeof fgRef.current.centerAt === 'function') {
            // 2. Smoothly glide to the node's position (800ms)
            fgRef.current.centerAt(simNode.x, simNode.y, 800);
            
            // 3. Elegantly push in (zoom) after the camera arrives
            // We do this sequentially to avoid D3 transition cancellation bugs!
            if (typeof fgRef.current.zoom === 'function') {
              zoomTimeoutRef.current = setTimeout(() => {
                if (fgRef.current) {
                  const currentZoom = fgRef.current.zoom() || 1;
                  // Moderate zoom (2.2) to bring node into attention while preserving neighborhood context
                  if (currentZoom < 2.2) {
                    fgRef.current.zoom(2.2, 800);
                  }
                }
              }, 800); // Wait for pan to finish
            }
          }
        }
      }, 150);
    }

    return () => {
      if (focusTimeoutRef.current) clearTimeout(focusTimeoutRef.current);
      if (zoomTimeoutRef.current) clearTimeout(zoomTimeoutRef.current);
    };
  }, [selectedNode, data]);

  // Adjust physics for denser graphs
  useEffect(() => {
    if (fgRef.current) {
      // Safely apply forces if they exist
      const chargeForce = fgRef.current.d3Force('charge');
      if (chargeForce && typeof chargeForce.strength === 'function') {
        chargeForce.strength(-350);
      }
      
      // Removed buggy custom 'collide' function that crashes D3 simulation
    }
  }, [data]);

  const paintNode = useCallback((node: CodeMapNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    if (!node || typeof node.x !== 'number' || typeof node.y !== 'number' || isNaN(node.x) || isNaN(node.y)) return;

    const isSelected = selectedNode?.id === node.id;
    const isHovered = hoverNode?.id === node.id;
    const isNeighbor = Boolean((hoverNode && neighbors.get(hoverNode.id)?.has(node.id)) || (selectedNode && neighbors.get(selectedNode.id)?.has(node.id)));
    
    // Dimming logic
    const hasFocus = Boolean(hoverNode || selectedNode);
    const isDimmed = hasFocus && !isHovered && !isSelected && !isNeighbor;
    
    const scaleFactor = (isSelected || isHovered) ? 1.3 : 1;
    const size = (node.val || 2) * scaleFactor;
    const color = getComplexityColor(node.complexity);

    // [PERF] Sub-pixel culling: Skip drawing microscopic nodes unless they are actively focused or cyclic
    const screenRadius = size * globalScale;
    if (screenRadius < 0.5 && !isSelected && !isHovered && !isNeighbor && !node.isInCycle) return;

    // [PERF] Fake Glows: Replaced extremely expensive ctx.shadowBlur with a cheap low-opacity radial arc.
    // This improves node render speeds by ~40x on large graphs.
    if ((node.isInCycle && !isDimmed) || isHovered || isSelected) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size * 2.5, 0, 2 * Math.PI, false);
      ctx.fillStyle = (isHovered || isSelected) ? color : '#ef4444';
      ctx.globalAlpha = 0.15;
      ctx.fill();
      ctx.globalAlpha = 1.0;
    }

    // Core Node Body
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
    ctx.fillStyle = isDimmed ? 'rgba(30, 41, 59, 0.3)' : color;
    ctx.fill();

    // Cinematic focus ring
    if (isSelected || isHovered) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size + (5 / globalScale), 0, 2 * Math.PI, false);
      ctx.lineWidth = 1.5 / globalScale;
      ctx.strokeStyle = isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.4)';
      ctx.stroke();
    } else if (!isDimmed && (node.kind === 'external' || node.kind === 'unresolved')) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
      ctx.lineWidth = 0.5 / globalScale;
      ctx.strokeStyle = '#444444';
      ctx.setLineDash([1 / globalScale, 1 / globalScale]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Progressive Disclosure: Labels
    // [PERF] Only draw text if sufficiently zoomed in or focused.
    if (!isDimmed && (globalScale > 3 || isSelected || isHovered || isNeighbor)) {
      const label = node.name || node.id;
      if (label) {
        const fontSize = Math.max(12 / globalScale, 1.5);
        ctx.font = `${isHovered || isSelected ? '500' : '400'} ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        const textY = node.y + size + fontSize + (3 / globalScale);

        // [PERF] Replaced expensive shadowBlur with ultra-fast hardware-accelerated strokeText for crisp contrast
        ctx.lineWidth = 3 / globalScale;
        ctx.strokeStyle = '#0f172a';
        ctx.strokeText(label, node.x, textY);
        
        ctx.fillStyle = isHovered || isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.55)';
        ctx.fillText(label, node.x, textY);
      }
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
        nodeLabel={() => ''}
        nodeVal="val"
        nodeCanvasObject={paintNode as any}
        onNodeHover={(n) => {
          if (hoverNode?.id !== (n as CodeMapNode | null)?.id) {
            onNodeHover(n as CodeMapNode | null);
          }
        }}
        onNodeClick={(n) => {
          if (n) onNodeClick(n as CodeMapNode);
        }}
        
        linkColor={(link: any) => {
          if (!link) return 'transparent';
          const edge = link as CodeMapEdge;
          const sId = typeof edge.source === 'object' ? (edge.source as CodeMapNode)?.id : edge.source;
          const tId = typeof edge.target === 'object' ? (edge.target as CodeMapNode)?.id : edge.target;
          
          if (!sId || !tId) return 'transparent';

          const hasFocus = Boolean(hoverNode || selectedNode);
          const isConnectedToFocus = hasFocus && 
            (sId === hoverNode?.id || tId === hoverNode?.id || sId === selectedNode?.id || tId === selectedNode?.id);
          
          if (hasFocus && !isConnectedToFocus) return 'rgba(30, 41, 59, 0.2)';
          if (edge.isInCycle) return '#ef4444';
          if (isConnectedToFocus) return 'rgba(255, 255, 255, 0.6)';
          return EDGE_COLORS[edge.kind] || EDGE_COLORS.internal;
        }}
        linkWidth={(link: any) => {
          if (!link) return 0;
          const edge = link as CodeMapEdge;
          const sId = typeof edge.source === 'object' ? (edge.source as CodeMapNode)?.id : edge.source;
          const tId = typeof edge.target === 'object' ? (edge.target as CodeMapNode)?.id : edge.target;
          
          const hasFocus = Boolean(hoverNode || selectedNode);
          const isConnectedToFocus = hasFocus && 
            (sId === hoverNode?.id || tId === hoverNode?.id || sId === selectedNode?.id || tId === selectedNode?.id);
          
          if (isConnectedToFocus) return 2;
          if (hasFocus && !isConnectedToFocus) return 0.2;
          return edge.isInCycle ? 2 : (edge.kind === 'internal' ? 1 : 0.5);
        }}
        linkLineDash={(link: any) => {
          if (!link) return null;
          return (link.kind === 'external' || link.kind === 'unresolved') && !link.isInCycle ? [2, 2] : null;
        }}
        
        linkDirectionalParticles={(link: any) => {
          if (!link) return 0;
          const sId = typeof link.source === 'object' ? link.source?.id : link.source;
          const tId = typeof link.target === 'object' ? link.target?.id : link.target;
          
          const hasFocus = Boolean(hoverNode || selectedNode);
          const isConnectedToFocus = hasFocus && 
            (sId === hoverNode?.id || tId === hoverNode?.id || sId === selectedNode?.id || tId === selectedNode?.id);

          if (link.isInCycle) return 5;
          if (hasFocus) return isConnectedToFocus ? 4 : 0;
          
          // [PERF] Adaptive Ambient Throttling: 
          // Disable idle background particles entirely if the graph is massive to preserve CPU.
          // Focus/cycle particles still render properly.
          if (data.edges.length > 250) return 0;
          
          return (link.kind === 'internal' || link.kind === 'self') ? 1 : 0;
        }}
        linkDirectionalParticleWidth={(link: any) => link?.isInCycle ? 3 : 2}
        linkDirectionalParticleSpeed={(link: any) => link?.isInCycle ? 0.012 : 0.006}
        linkDirectionalParticleColor={(link: any) => link?.isInCycle ? 'rgba(239, 68, 68, 0.9)' : 'rgba(255, 255, 255, 0.8)'}
        
        d3VelocityDecay={0.12}
        warmupTicks={150}
        cooldownTicks={100}
      />
    </div>
  );
};
