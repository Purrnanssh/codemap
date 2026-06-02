import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { forceX, forceY } from 'd3-force';
import type { CodeMapGraph, CodeMapNode, CodeMapEdge } from '../../types/codemap';
import { getComplexityColor, EDGE_COLORS } from '../../utils/colors';

interface GraphViewerProps {
  data: CodeMapGraph;
  onNodeClick: (node: CodeMapNode) => void;
  onNodeHover: (node: CodeMapNode | null) => void;
  selectedNode: CodeMapNode | null;
  hoverNode: CodeMapNode | null;
  isSidebarOpen: boolean;
}

export const GraphViewer: React.FC<GraphViewerProps> = ({ data, onNodeClick, onNodeHover, selectedNode, hoverNode, isSidebarOpen }) => {
  const fgRef = useRef<any>(null);
  const isEngineRunning = useRef(true);
  const [dimensions, setDimensions] = useState({ width: window.innerWidth, height: window.innerHeight });
  const [dragNode, setDragNode] = useState<CodeMapNode | null>(null);

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
    const handleResize = () => {
      // Offset by 320px (w-80 sidebar) + 16px (left-4 margin) + 16px (right spacing) = 352px when open
      // This forces the React Force Graph to physically shrink its WebGL canvas
      // which automatically shifts D3's center of gravity, causing the nodes to seamlessly glide
      // to the new visual center of the available space.
      const sidebarOffset = isSidebarOpen ? 352 : 0;
      setDimensions({ 
        width: window.innerWidth - sidebarOffset, 
        height: window.innerHeight 
      });
    };
    
    handleResize(); // Trigger immediately when sidebar state changes
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isSidebarOpen]);

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
        // Less repulsion for smaller graphs (like module view), but scale relative to node size (val)
        // so larger/higher-degree nodes become heavier anchor points that push surrounding clusters visually.
        const baseRepulsion = data.nodes.length < 200 ? -40 : -100;
        chargeForce.strength((n: any) => baseRepulsion * Math.max(1, Math.sqrt(n.val || 1)));
      }
      
      // Add a gentle gravity force to keep disconnected subgraphs from flying into deep space
      // which ruins the camera's auto-zoom and causes all nodes to be culled
      fgRef.current.d3Force('x', forceX(0).strength(0.05));
      fgRef.current.d3Force('y', forceY(0).strength(0.05));
    }
  }, [data]);

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    if (!node || typeof node.x !== 'number' || typeof node.y !== 'number' || isNaN(node.x) || isNaN(node.y)) return;

    const isSelected = selectedNode?.id === node.id;
    const isHovered = hoverNode?.id === node.id;
    const isDragged = dragNode?.id === node.id;
    const isNeighbor = Boolean(
      (hoverNode && neighbors.get(hoverNode.id)?.has(node.id)) || 
      (selectedNode && neighbors.get(selectedNode.id)?.has(node.id)) ||
      (dragNode && neighbors.get(dragNode.id)?.has(node.id))
    );
    
    // Ambient Galaxy Drift & Breathing Effect
    // Applies a subtle, perpetual floating motion when the physics engine settles.
    // Major hubs move less; peripheral nodes drift more.
    if (!isEngineRunning.current && node.isStabilized && !isDragged && !isSelected && typeof node.baseX === 'number' && typeof node.baseY === 'number') {
      // Time scalar increased for visible, continuous movement
      const t = Date.now() / 1000; 
      
      // Subtle cluster breathing: expands/contracts by ~3% smoothly
      const breathing = Math.sin(t * 0.4) * 0.03;
      
      // Procedural drift offset: 3x larger amplitude so it reads clearly within 2-3 seconds
      const amplitude = Math.max(0.4, 4.5 / Math.sqrt(node.val || 2));
      const offsetX = Math.sin(t * 0.8 + (node.seedX || 0)) * amplitude;
      const offsetY = Math.cos(t * 0.9 + (node.seedY || 0)) * amplitude;
      
      // Update coordinates dynamically. react-force-graph will use these on the next frame to draw edges.
      node.x = node.baseX * (1 + breathing) + offsetX;
      node.y = node.baseY * (1 + breathing) + offsetY;
    }
    
    // Dimming logic: Only dim the graph when a node is explicitly clicked (selectedNode), NOT on hover or drag.
    // The user requested: "Preserve graph visibility. Dragging should NEVER hide the graph".
    const isDimmed = Boolean(selectedNode) && !isSelected && !isNeighbor;
    
    const scaleFactor = isDragged ? 1.5 : ((isSelected || isHovered) ? 1.3 : 1);
    const size = (node.val || 2) * scaleFactor;
    const color = getComplexityColor(node.complexity);

    // [PERF] Sub-pixel culling: Skip drawing microscopic nodes unless they are actively focused or cyclic
    const screenRadius = size * globalScale;
    if (screenRadius < 0.5 && !isSelected && !isHovered && !isDragged && !isNeighbor && !node.isInCycle) return;

    // Drag Glow Effect
    if (isDragged) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size * 2.5, 0, 2 * Math.PI, false);
      ctx.fillStyle = '#ffffff';
      ctx.globalAlpha = 0.2;
      ctx.fill();
      ctx.globalAlpha = 1.0;
    }

    // [PERF] Fake Glows for Cycle/Hover/Select
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
    if (isSelected || isHovered || isDragged) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size + (5 / globalScale), 0, 2 * Math.PI, false);
      ctx.lineWidth = (isDragged ? 2.5 : 1.5) / globalScale;
      ctx.strokeStyle = (isSelected || isDragged) ? '#ffffff' : 'rgba(255, 255, 255, 0.4)';
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
    // Show labels if zoomed in, explicitly selected, or if it's a first-degree connection to the selected node.
    // Hover labels are disabled to keep hover purely visual and minimal.
    if (!isDimmed && (globalScale > 3 || isSelected || (selectedNode && isNeighbor))) {
      const label = node.name || node.id;
      if (label) {
        const fontSize = Math.max(12 / globalScale, 1.5);
        ctx.font = `${isSelected ? '500' : '400'} ${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        const textY = node.y + size + fontSize + (3 / globalScale);

        // [PERF] Replaced expensive shadowBlur with ultra-fast hardware-accelerated strokeText for crisp contrast
        ctx.lineWidth = 3 / globalScale;
        ctx.strokeStyle = '#0f172a';
        ctx.strokeText(label, node.x, textY);
        
        ctx.fillStyle = isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.55)';
        ctx.fillText(label, node.x, textY);
      }
    }
  }, [selectedNode, hoverNode, dragNode, neighbors]);

  return (
    <div 
      className={`absolute inset-y-0 right-0 bg-transparent overflow-hidden ${dragNode ? 'cursor-grabbing' : (hoverNode ? 'cursor-grab' : 'cursor-grab active:cursor-grabbing')} transition-all duration-300 ease-[cubic-bezier(0.175,0.885,0.32,1.275)]`}
      style={{ left: isSidebarOpen ? '352px' : '0px' }}
    >
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        nodeId="id"
        width={dimensions.width}
        height={dimensions.height}
        nodeLabel={() => ''}
        nodeVal="val"
        nodeCanvasObject={paintNode as any}
        nodePointerAreaPaint={(node: any, color, ctx) => {
          // Expand the interactive hit area for small nodes so they are consistently draggable
          const size = Math.max(((node.val || 2) * 1.3), 5);
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
          ctx.fill();
        }}
        onNodeHover={(n) => {
          if (hoverNode?.id !== (n as CodeMapNode | null)?.id) {
            onNodeHover(n as CodeMapNode | null);
          }
        }}
        onNodeClick={(n) => {
          if (n) onNodeClick(n as CodeMapNode);
        }}
        
        onNodeDrag={(n: any) => {
          if (dragNode?.id !== n.id) {
            setDragNode(n as CodeMapNode);
          }
          n.fx = n.x;
          n.fy = n.y;
        }}
        onNodeDragEnd={(n: any) => {
          setDragNode(null);
          // Release physics lock so node settles naturally back into the simulation
          n.fx = undefined;
          n.fy = undefined;
          
          // Reheat the simulation slightly so the surrounding nodes react smoothly
          if (fgRef.current) {
            fgRef.current.d3ReheatSimulation();
          }
        }}
        
        onEngineTick={() => {
          isEngineRunning.current = true;
        }}
        onEngineStop={() => {
          isEngineRunning.current = false;
          // When simulation settles, snapshot positions for the ambient galaxy drift effect
          if (graphData && graphData.nodes) {
            graphData.nodes.forEach((n: any) => {
              n.baseX = n.x;
              n.baseY = n.y;
              if (n.seedX === undefined) {
                n.seedX = Math.random() * 1000;
                n.seedY = Math.random() * 1000;
                n.isStabilized = true;
              }
            });
          }
        }}
        
        linkColor={(link: any) => {
          if (!link) return 'transparent';
          const edge = link as CodeMapEdge;
          const sId = typeof edge.source === 'object' ? (edge.source as CodeMapNode)?.id : edge.source;
          const tId = typeof edge.target === 'object' ? (edge.target as CodeMapNode)?.id : edge.target;
          
          if (!sId || !tId) return 'transparent';

          // Only isolate unselected edges when explicitly clicked
          const hasSelection = Boolean(selectedNode);
          const isConnectedToFocus = (hoverNode && (sId === hoverNode.id || tId === hoverNode.id)) || 
                                     (selectedNode && (sId === selectedNode.id || tId === selectedNode.id));
          
          if (hasSelection && !(selectedNode && (sId === selectedNode.id || tId === selectedNode.id))) return 'rgba(30, 41, 59, 0.2)';
          if (edge.isInCycle) return '#ef4444';
          if (isConnectedToFocus) return 'rgba(255, 255, 255, 0.6)';
          return EDGE_COLORS[edge.kind] || EDGE_COLORS.internal;
        }}
        linkWidth={(link: any) => {
          if (!link) return 0;
          const edge = link as CodeMapEdge;
          const sId = typeof edge.source === 'object' ? (edge.source as CodeMapNode)?.id : edge.source;
          const tId = typeof edge.target === 'object' ? (edge.target as CodeMapNode)?.id : edge.target;
          
          const hasSelection = Boolean(selectedNode);
          const isConnectedToFocus = (hoverNode && (sId === hoverNode.id || tId === hoverNode.id)) || 
                                     (selectedNode && (sId === selectedNode.id || tId === selectedNode.id));
          
          if (isConnectedToFocus) return 2;
          if (hasSelection && !(selectedNode && (sId === selectedNode.id || tId === selectedNode.id))) return 0.2;
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
          
          const isConnectedToFocus = (hoverNode && (sId === hoverNode.id || tId === hoverNode.id)) || 
                                     (selectedNode && (sId === selectedNode.id || tId === selectedNode.id));

          if (link.isInCycle) return 5;
          if (isConnectedToFocus) return 4;
          
          // Randomize slightly so they don't all look uniform
          return Math.random() > 0.5 ? 2 : 1;
        }}
        linkDirectionalParticleWidth={(link: any) => link?.isInCycle ? 3 : 1.5}
        linkDirectionalParticleSpeed={(link: any) => link?.isInCycle ? 0.012 : (0.003 + Math.random() * 0.003)}
        linkDirectionalParticleColor={(link: any) => {
          if (link?.isInCycle) return 'rgba(239, 68, 68, 0.9)';
          
          const sId = typeof link.source === 'object' ? link.source?.id : link.source;
          const tId = typeof link.target === 'object' ? link.target?.id : link.target;
          const isConnectedToFocus = (hoverNode && (sId === hoverNode.id || tId === hoverNode.id)) || 
                                     (selectedNode && (sId === selectedNode.id || tId === selectedNode.id));
                                     
          if (isConnectedToFocus) return 'rgba(255, 255, 255, 0.9)';
          return 'rgba(100, 150, 255, 0.4)'; // Cyberpunk ambient data stream color
        }}
        
        d3VelocityDecay={0.12}
        warmupTicks={150}
        cooldownTicks={100}
      />
    </div>
  );
};
