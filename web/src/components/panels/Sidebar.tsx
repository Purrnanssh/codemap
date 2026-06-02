
import { motion, AnimatePresence } from 'framer-motion';
import type { Hotspot } from '../../types/codemap';
import { Activity, Zap, PanelLeftOpen, PanelLeftClose } from 'lucide-react';
import { clsx } from 'clsx';
import { getComplexityColor } from '../../utils/colors';

interface SidebarProps {
  hotspots: Hotspot[];
  onHotspotClick: (hotspot: Hotspot) => void;
  selectedId: string | null;
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ hotspots, onHotspotClick, selectedId, isOpen, onToggle }) => {

  return (
    <AnimatePresence mode="wait">
      {!isOpen ? (
        <motion.button
          key="collapsed-button"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          transition={{ duration: 0.2 }}
          onClick={onToggle}
          className="absolute top-6 left-6 z-20 w-10 h-10 rounded-xl glass-panel flex items-center justify-center hover:bg-white/5 transition-colors group shadow-lg"
          title="Expand sidebar"
        >
          <PanelLeftOpen className="w-5 h-5 text-slate-400 group-hover:text-primary transition-colors" />
        </motion.button>
      ) : (
        <motion.div 
          key="expanded-sidebar"
          initial={{ x: -300, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -300, opacity: 0 }}
          transition={{ type: 'spring', damping: 30, stiffness: 400 }}
          className="absolute top-4 left-4 bottom-4 w-80 glass-panel flex flex-col overflow-hidden z-20 shadow-2xl"
        >
          <div className="p-4 border-b border-panel-border flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <Activity className="text-primary w-5 h-5 shrink-0" />
              <h2 className="text-base font-medium text-foreground tracking-tight whitespace-nowrap overflow-hidden">
                CodeMap
              </h2>
            </div>
            
            <button 
              onClick={onToggle}
              className="text-slate-400 hover:text-white transition-colors p-1.5 rounded-md hover:bg-white/10"
              title="Collapse sidebar"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          <div className="flex flex-col flex-1 overflow-hidden">
            <div className="p-4 bg-slate-800/50 shrink-0">
              <div className="flex items-center gap-2 mb-1.5">
                <Zap className="text-hotspot w-3.5 h-3.5" />
                <h3 className="text-xs font-medium text-slate-400 uppercase tracking-widest">Top Hotspots</h3>
              </div>
              <p className="text-xs text-slate-400 mb-0">Ranked by Complexity × Fan-in</p>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {hotspots.map((hotspot) => (
                <button
                  key={hotspot.id}
                  onClick={() => onHotspotClick(hotspot)}
                  className={clsx(
                    "w-full text-left p-3 rounded-lg transition-colors duration-200 flex items-start gap-3 relative",
                    selectedId === hotspot.id ? "bg-white/5" : "hover:bg-slate-800/40"
                  )}
                >
                  {selectedId === hotspot.id && (
                    <motion.div layoutId="sidebarActive" className="absolute left-0 top-2 bottom-2 w-[3px] bg-primary rounded-r-full" transition={{ type: "spring", stiffness: 400, damping: 30 }} />
                  )}
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
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
