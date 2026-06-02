// Matches backend color palette
export const COMPLEXITY_PALETTE = [
  "#e0f3ff",  // 1: very light blue
  "#c7e9f1",  // 2
  "#a8d5e2",  // 3
  "#80c1d4",  // 4
  "#fce7c5",  // 5: shifting to warm
  "#fbcfa0",  // 6
  "#f9a875",  // 7
  "#f47e51",  // 8
  "#e45a3a",  // 9
  "#c93a2c",  // 10
  "#9b1e1e",  // 11+: saturated dark red
];

export function getComplexityColor(complexity: number | undefined): string {
  if (!complexity) return '#666666'; // Default for synthetic
  if (complexity < 1) return COMPLEXITY_PALETTE[0];
  if (complexity > 11) return COMPLEXITY_PALETTE[10];
  return COMPLEXITY_PALETTE[complexity - 1];
}

export const EDGE_COLORS = {
  internal: 'rgba(255, 255, 255, 0.4)',
  self: 'rgba(70, 130, 180, 0.8)',
  external: 'rgba(153, 153, 153, 0.3)',
  unresolved: 'rgba(255, 0, 0, 0.3)'
};
