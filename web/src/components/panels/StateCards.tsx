import { motion } from 'framer-motion';
import { FileCode2, AlertTriangle, ArrowLeft, CheckCircle2, FileQuestion, ArrowRight } from 'lucide-react';
import type { GraphSummary } from '../../types/codemap';

interface EmptyStateCardProps {
  summary?: GraphSummary;
  onReset: () => void;
}

export function EmptyStateCard({ summary, onReset }: EmptyStateCardProps) {
  return (
    <div className="min-h-screen bg-background cinematic-bg flex items-center justify-center p-6 relative">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-xl w-full relative z-10"
      >
        <div className="bg-slate-900/40 border border-white/10 rounded-2xl p-8 backdrop-blur-xl shadow-2xl overflow-hidden relative">
          
          {/* Top glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-[1px] bg-gradient-to-r from-transparent via-blue-500/50 to-transparent" />
          
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 shadow-[0_0_30px_rgba(255,255,255,0.05)] flex items-center justify-center mb-6">
              <FileQuestion className="w-8 h-8 text-blue-400" />
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight mb-2">No Python Files Detected</h2>
            <p className="text-slate-400 text-sm font-medium leading-relaxed max-w-sm">
              This repository was successfully scanned, but no supported source files were found to build a graph.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
            {/* Repository Diagnostics */}
            {summary && (
              <div className="bg-black/30 rounded-xl p-5 border border-white/5">
                <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                  <FileCode2 className="w-4 h-4 text-slate-400" />
                  Repository Summary
                </h3>
                <div className="text-slate-300 text-sm mb-3">
                  <span className="text-white font-medium">{summary.files_scanned}</span> files detected
                </div>
                {summary.detected_extensions.length > 0 && (
                  <div className="space-y-1.5">
                    <div className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-2">File Types</div>
                    {summary.detected_extensions.slice(0, 5).map(ext => (
                      <div key={ext} className="flex items-center gap-2 text-sm text-slate-300">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
                        {ext}
                      </div>
                    ))}
                    {summary.detected_extensions.length > 5 && (
                      <div className="text-xs text-slate-500 mt-1 italic">
                        + {summary.detected_extensions.length - 5} more types
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Language Support Map */}
            <div className="bg-black/30 rounded-xl p-5 border border-white/5">
              <h3 className="text-sm font-semibold text-white mb-3">CodeMap Engine</h3>
              
              <div className="space-y-4">
                <div>
                  <div className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-2">Currently Supported</div>
                  <div className="flex items-center gap-2 text-sm text-white font-medium">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Python
                  </div>
                </div>

                <div>
                  <div className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-2">Coming Soon</div>
                  <div className="grid grid-cols-2 gap-x-2 gap-y-1.5">
                    {['JavaScript', 'TypeScript', 'React', 'Java', 'Go'].map(lang => (
                      <div key={lang} className="flex items-center gap-2 text-sm text-slate-400">
                        <span className="w-1 h-1 rounded-full bg-slate-700"></span>
                        {lang}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-6 border-t border-white/5 flex flex-col items-center">
            <button 
              onClick={onReset}
              className="bg-white text-black font-medium text-sm rounded-xl px-6 py-3 hover:bg-slate-200 transition-colors flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Analyze Another Repository
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

interface ErrorStateCardProps {
  errorMsg: string;
  onReset: () => void;
}

export function ErrorStateCard({ errorMsg, onReset }: ErrorStateCardProps) {
  return (
    <div className="min-h-screen bg-background cinematic-bg flex items-center justify-center p-6 relative">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md w-full relative z-10"
      >
        <div className="bg-slate-900/40 border border-red-500/20 rounded-2xl p-8 backdrop-blur-xl shadow-2xl relative overflow-hidden">
          {/* Top glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-[1px] bg-gradient-to-r from-transparent via-red-500/50 to-transparent" />
          
          <div className="flex flex-col items-center text-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 shadow-[0_0_30px_rgba(239,68,68,0.1)] flex items-center justify-center mb-6">
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight mb-2">Repository Scan Failed</h2>
            <p className="text-slate-400 text-sm font-medium">
              We encountered a network or backend issue while attempting to parse this workspace.
            </p>
          </div>

          <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-4 mb-8 text-left">
            <div className="text-xs text-red-400/80 font-medium uppercase tracking-wider mb-2">Reason</div>
            <p className="text-red-300 font-mono text-sm break-words">
              {errorMsg}
            </p>
          </div>

          <button 
            onClick={onReset}
            className="w-full bg-slate-800 border border-white/10 text-white font-medium text-sm rounded-xl px-6 py-3 hover:bg-slate-700 transition-colors flex justify-center items-center gap-2"
          >
            Try another repository
            <ArrowRight className="w-4 h-4 opacity-50" />
          </button>
        </div>
      </motion.div>
    </div>
  );
}
