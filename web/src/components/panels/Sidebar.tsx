
import { motion } from 'framer-motion';
import type { Hotspot } from '../../types/codemap';
import { Activity, Zap } from 'lucide-react';
import { clsx } from 'clsx';
import { getComplexityColor } from '../../utils/colors';

interface SidebarProps {
  hotspots: Hotspot[];
  onHotspotClick: (hotspot: Hotspot) => void;
  selectedId: string | null;
}

export const Sidebar: React.FC<SidebarProps> = ({ hotspots, onHotspotClick, selectedId }) => {
  return (
    <motion.div 
      initial={{ x: -300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', damping: 20 }}
      className="absolute top-4 left-4 bottom-4 w-80 glass-panel flex flex-col overflow-hidden z-10"
    >
      <div className="p-4 border-b border-panel-border flex items-center gap-2">
        <Activity className="text-primary w-5 h-5" />
        <h2 className="text-lg font-semibold text-foreground tracking-wide">CodeMap</h2>
      </div>

      <div className="p-4 bg-slate-800/50">
        <div className="flex items-center gap-2 mb-2">
          <Zap className="text-hotspot w-4 h-4" />
          <h3 className="text-sm font-medium text-slate-300 uppercase tracking-wider">Top Hotspots</h3>
        </div>
        <p className="text-xs text-slate-400 mb-4">Ranked by Complexity × Fan-in</p>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {hotspots.map((hotspot) => (
          <button
            key={hotspot.id}
            onClick={() => onHotspotClick(hotspot)}
            className={clsx(
              "w-full text-left p-3 rounded-lg transition-colors flex items-start gap-3",
              selectedId === hotspot.id ? "bg-primary/20 border border-primary/30" : "hover:bg-slate-800/60"
            )}
          >
            <div 
              className="w-2 h-2 rounded-full mt-1.5 shrink-0" 
              style={{ backgroundColor: getComplexityColor(hotspot.complexity) }}
            />
            <div className="overflow-hidden">
              <div className="text-sm font-medium text-slate-200 truncate" title={hotspot.name}>
                {hotspot.name}
              </div>
              <div className="text-xs text-slate-400 flex gap-3 mt-1">
                <span>Score: <span className="text-slate-300 font-medium">{hotspot.score}</span></span>
                <span>Cx: <span className="text-slate-300">{hotspot.complexity}</span></span>
                <span>In: <span className="text-slate-300">{hotspot.fanIn}</span></span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </motion.div>
  );
};
