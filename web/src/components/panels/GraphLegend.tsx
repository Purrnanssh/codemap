
import { COMPLEXITY_PALETTE, EDGE_COLORS } from '../../utils/colors';

interface GraphLegendProps {
  isInspectorOpen?: boolean;
}

export const GraphLegend: React.FC<GraphLegendProps> = ({ isInspectorOpen }) => {
  return (
    <div 
      className={`absolute bottom-4 glass-panel p-4 w-64 z-10 space-y-4 transition-all duration-500 ease-[cubic-bezier(0.175,0.885,0.32,1.275)] ${
        isInspectorOpen ? 'right-[350px]' : 'right-4'
      }`}
    >
      <div>
        <h3 className="text-xs uppercase text-slate-400 font-semibold mb-2 tracking-wider">Complexity</h3>
        <div className="flex w-full h-3 rounded-full overflow-hidden bg-slate-800">
          {COMPLEXITY_PALETTE.map((color, i) => (
            <div key={i} className="flex-1 h-full" style={{ backgroundColor: color }} />
          ))}
        </div>
        <div className="flex justify-between text-[10px] text-slate-500 mt-1">
          <span>Low (1)</span>
          <span>High (11+)</span>
        </div>
      </div>

      <div>
        <h3 className="text-xs uppercase text-slate-400 font-semibold mb-2 tracking-wider">Edges</h3>
        <div className="space-y-2 text-xs text-slate-300">
          <div className="flex items-center gap-2">
            <div className="w-6 h-[2px]" style={{ backgroundColor: EDGE_COLORS.internal }} />
            <span>Internal Call</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-[2px]" style={{ backgroundColor: EDGE_COLORS.self }} />
            <span>Self Call</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-[1px] border-b border-dashed" style={{ borderColor: EDGE_COLORS.external }} />
            <span className="text-slate-400">External</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-[1px] border-b border-dotted" style={{ borderColor: EDGE_COLORS.unresolved }} />
            <span className="text-red-400/80">Unresolved</span>
          </div>
        </div>
      </div>
    </div>
  );
};
