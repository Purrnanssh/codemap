import type { CodeMapGraph, CodeMapNode, CodeMapEdge } from '../types/codemap';

/**
 * Tarjan's Strongly Connected Components algorithm to find cycles.
 */
export function findCycles(graph: CodeMapGraph): Set<string> {
  let index = 0;
  const stack: string[] = [];
  const indices = new Map<string, number>();
  const lowlinks = new Map<string, number>();
  const onStack = new Set<string>();
  const cycles = new Set<string>();

  // Build adjacency list
  const adj = new Map<string, string[]>();
  graph.nodes.forEach(n => adj.set(n.id, []));
  graph.edges.forEach(e => {
    const sourceId = typeof e.source === 'object' ? (e.source as CodeMapNode).id : e.source;
    const targetId = typeof e.target === 'object' ? (e.target as CodeMapNode).id : e.target;
    if (adj.has(sourceId)) {
      adj.get(sourceId)!.push(targetId as string);
    }
  });

  function strongconnect(v: string) {
    indices.set(v, index);
    lowlinks.set(v, index);
    index++;
    stack.push(v);
    onStack.add(v);

    const neighbors = adj.get(v) || [];
    for (const w of neighbors) {
      if (!indices.has(w)) {
        strongconnect(w);
        lowlinks.set(v, Math.min(lowlinks.get(v)!, lowlinks.get(w)!));
      } else if (onStack.has(w)) {
        lowlinks.set(v, Math.min(lowlinks.get(v)!, indices.get(w)!));
      }
    }

    if (lowlinks.get(v) === indices.get(v)) {
      const scc: string[] = [];
      let w: string;
      do {
        w = stack.pop()!;
        onStack.delete(w);
        scc.push(w);
      } while (w !== v);

      // Only count cycles of length > 1 (ignore self-edges for architectural cycles)
      if (scc.length > 1) {
        scc.forEach(node => cycles.add(node));
      }
    }
  }

  graph.nodes.forEach(n => {
    if (!indices.has(n.id)) {
      strongconnect(n.id);
    }
  });

  return cycles;
}

/**
 * Reduces a symbol-level graph to a module-level graph.
 */
export function buildModuleGraph(symbolGraph: CodeMapGraph): CodeMapGraph {
  const moduleNodes = new Map<string, CodeMapNode>();
  const moduleEdges = new Map<string, CodeMapEdge>();

  // Extract modules
  symbolGraph.nodes.forEach(node => {
    const modId = node.module || node.id.split('.')[0] || 'unknown';
    if (!moduleNodes.has(modId)) {
      moduleNodes.set(modId, {
        id: modId,
        name: modId,
        kind: node.kind === 'function' ? 'function' : node.kind,
        complexity: node.complexity || 1, // Aggregate later if needed
      });
    } else {
      const m = moduleNodes.get(modId)!;
      if (node.complexity) {
        m.complexity = Math.max(m.complexity || 1, node.complexity);
      }
    }
  });

  // Extract edges
  symbolGraph.edges.forEach(edge => {
    const sId = typeof edge.source === 'object' ? (edge.source as CodeMapNode).id : edge.source;
    const tId = typeof edge.target === 'object' ? (edge.target as CodeMapNode).id : edge.target;
    
    const sourceNode = symbolGraph.nodes.find(n => n.id === sId);
    const targetNode = symbolGraph.nodes.find(n => n.id === tId);

    const sMod = sourceNode?.module || sId.split('.')[0] || 'unknown';
    const tMod = targetNode?.module || tId.split('.')[0] || 'unknown';

    if (sMod === tMod) return; // Skip internal module calls for module graph

    const edgeId = `${sMod}->${tMod}`;
    if (!moduleEdges.has(edgeId)) {
      moduleEdges.set(edgeId, {
        source: sMod,
        target: tMod,
        kind: edge.kind === 'internal' ? 'internal' : 'external',
      });
    }
  });

  return {
    nodes: Array.from(moduleNodes.values()),
    edges: Array.from(moduleEdges.values())
  };
}

/**
 * Annotates graph with fan-in sizes and cycle flags.
 */
export function enhanceGraph(graph: CodeMapGraph): CodeMapGraph {
  const fanInMap: Record<string, number> = {};
  graph.edges.forEach(e => {
    const t = typeof e.target === 'object' ? (e.target as CodeMapNode).id : e.target as string;
    fanInMap[t] = (fanInMap[t] || 0) + 1;
  });

  const cyclicNodeIds = findCycles(graph);

  const nodes = graph.nodes.map(n => ({
    ...n,
    val: Math.min(Math.max((fanInMap[n.id] || 0) * 0.8 + 3, 3), 20),
    isInCycle: cyclicNodeIds.has(n.id)
  }));

  const edges = graph.edges.map(e => {
    const sId = typeof e.source === 'object' ? (e.source as CodeMapNode).id : e.source as string;
    const tId = typeof e.target === 'object' ? (e.target as CodeMapNode).id : e.target as string;
    return {
      ...e,
      isInCycle: cyclicNodeIds.has(sId) && cyclicNodeIds.has(tId)
    };
  });

  return { nodes, edges };
}
