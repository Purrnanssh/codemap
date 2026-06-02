export interface CodeMapNode {
  id: string;
  kind: 'function' | 'external' | 'unresolved';
  module?: string;
  class_name?: string;
  name?: string;
  line?: number;
  is_method?: boolean;
  is_async?: boolean;
  complexity?: number;
  isInCycle?: boolean;
  // Force graph injected properties
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
  color?: string;
  val?: number; // size
}

export interface CodeMapEdge {
  source: string | CodeMapNode;
  target: string | CodeMapNode;
  kind: 'internal' | 'self' | 'external' | 'unresolved';
  isInCycle?: boolean;
  call_count?: number;
  first_line?: number;
}

export interface CodeMapGraph {
  nodes: CodeMapNode[];
  edges: CodeMapEdge[];
}

export interface Hotspot {
  id: string;
  name: string;
  complexity: number;
  fanIn: number;
  score: number;
  node: CodeMapNode;
}

export type GraphMode = 'symbol' | 'module';


