import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { aiService } from '../../services/ai';
import type { CodeMapNode, CodeMapEdge } from '../../types/codemap';
import { X, Code, Box, AlertCircle, Sparkles } from 'lucide-react';
import { getComplexityColor } from '../../utils/colors';

function useAIExplanation(node: CodeMapNode | null, edges: CodeMapEdge[]) {
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!node) {
      setExplanation(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);

    const incoming = edges
      .filter(e => {
        const targetId = typeof e.target === 'object' ? e.target.id : e.target;
        return targetId === node.id;
      })
      .map(e => typeof e.source === 'object' ? e.source.id : e.source as string);

    const outgoing = edges
      .filter(e => {
        const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
        return sourceId === node.id;
      })
      .map(e => typeof e.target === 'object' ? e.target.id : e.target as string);

    aiService.generateExplanation({ node, incoming, outgoing })
      .then(res => {
        if (isMounted) {
          setExplanation(res);
          setIsLoading(false);
        }
      })
      .catch(err => {
        console.error("AI Error:", err);
        if (isMounted) setIsLoading(false);
      });

    return () => { isMounted = false; };
  }, [node, edges]);

  return { explanation, isLoading };
}

interface InspectorPanelProps {
  node: CodeMapNode | null;
  edges: CodeMapEdge[];
  onClose: () => void;
}

export const InspectorPanel: React.FC<InspectorPanelProps> = ({ node, edges, onClose }) => {
  if (!node) return null;

  const incoming = edges.filter(e => {
    const targetId = typeof e.target === 'object' ? e.target.id : e.target;
    return targetId === node.id;
  });
  const outgoing = edges.filter(e => {
    const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
    return sourceId === node.id;
  });

  const { explanation, isLoading } = useAIExplanation(node, edges);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ x: 300, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 300, opacity: 0 }}
        transition={{ type: 'spring', damping: 30, stiffness: 400 }}
        className="absolute top-4 right-4 bottom-4 w-80 glass-panel flex flex-col overflow-hidden z-10"
      >
        <div className="p-4 border-b border-panel-border flex items-start justify-between">
          <div className="flex items-center gap-2">
            {node.kind === 'function' ? <Code className="text-primary w-4 h-4" /> : 
             node.kind === 'external' ? <Box className="text-slate-400 w-4 h-4" /> :
             <AlertCircle className="text-red-400 w-4 h-4" />}
            <h2 className="text-sm font-medium text-foreground truncate max-w-[200px]" title={node.name || node.id}>
              {node.name || node.id.split('.').pop()}
            </h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          <div className="space-y-2">
            <h3 className="text-[10px] uppercase text-slate-500 font-medium tracking-widest">Details</h3>
            <div className="bg-slate-800/40 rounded-lg p-3 space-y-2 text-sm text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-500">Kind</span>
                <span className="capitalize">{node.kind}</span>
              </div>
              {node.module && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Module</span>
                  <span className="truncate ml-4">{node.module}</span>
                </div>
              )}
              {node.class_name && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Class</span>
                  <span>{node.class_name}</span>
                </div>
              )}
              {node.line && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Line</span>
                  <span>{node.line}</span>
                </div>
              )}
              {node.complexity !== undefined && (
                <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-700/50">
                  <span className="text-slate-500">McCabe Complexity</span>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getComplexityColor(node.complexity) }} />
                    <span className="font-medium text-white">{node.complexity}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-[10px] uppercase text-slate-500 font-medium tracking-widest">Metrics</h3>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-slate-800/40 rounded-lg p-3 text-center">
                <div className="text-2xl font-light text-white">{incoming.length}</div>
                <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Fan-In</div>
              </div>
              <div className="bg-slate-800/40 rounded-lg p-3 text-center">
                <div className="text-2xl font-light text-white">{outgoing.length}</div>
                <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Fan-Out</div>
              </div>
            </div>
          </div>
          <div className="space-y-2">
            <h3 className="text-[10px] uppercase text-slate-500 font-medium tracking-widest flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              AI Insights
            </h3>
            <div className="bg-slate-800/40 rounded-lg p-4 text-sm text-slate-300 min-h-[150px] relative">
              {isLoading ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-400">
                  <motion.div 
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                  >
                    <Sparkles className="w-6 h-6 text-indigo-500 mb-2" />
                  </motion.div>
                  <span className="animate-pulse">Analyzing architecture...</span>
                </div>
              ) : explanation ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5 }}
                >
                  <ReactMarkdown
                    components={{
                      h3: ({node, ...props}) => <h3 className="text-slate-200 font-semibold mb-2 mt-4 first:mt-0" {...props} />,
                      p: ({node, ...props}) => <p className="text-slate-300 mb-3 leading-relaxed" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc pl-4 my-2 text-slate-300 space-y-1" {...props} />,
                      li: ({node, ...props}) => <li className="mb-1" {...props} />,
                      a: ({node, ...props}) => <a className="text-indigo-400 hover:text-indigo-300 transition-colors" {...props} />,
                      strong: ({node, ...props}) => <strong className="text-slate-200 font-medium" {...props} />,
                      blockquote: ({node, ...props}) => <blockquote className="border-l-2 border-indigo-500 bg-indigo-500/10 px-3 py-2 rounded-r my-3 text-slate-300 italic" {...props} />,
                      code: ({node, ...props}) => <code className="bg-slate-900/50 text-indigo-300 px-1 py-0.5 rounded font-mono text-xs" {...props} />
                    }}
                  >
                    {explanation}
                  </ReactMarkdown>
                </motion.div>
              ) : null}
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
