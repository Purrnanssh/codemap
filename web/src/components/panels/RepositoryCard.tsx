import { motion } from 'framer-motion';
import { GitBranch, FolderCode, ExternalLink } from 'lucide-react';

interface RepositoryCardProps {
  workspacePath: string;
}

export function RepositoryCard({ workspacePath }: RepositoryCardProps) {
  // Try to parse the repository owner and name if it's a GitHub URL
  const isGithub = workspacePath.startsWith('https://github.com/');
  let displayName = workspacePath;
  let owner = '';
  let repo = '';
  
  if (isGithub) {
    try {
      const url = new URL(workspacePath);
      const parts = url.pathname.split('/').filter(Boolean);
      if (parts.length >= 2) {
        owner = parts[0];
        repo = parts[1];
        displayName = `${owner}/${repo}`;
      }
    } catch {
      // Fallback to raw string if parsing fails
    }
  } else {
    // Local path handling
    const parts = workspacePath.split('/').filter(Boolean);
    if (parts.length > 0) {
      displayName = parts[parts.length - 1];
    }
  }

  return (
    <motion.div 
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="absolute top-6 left-6 z-20"
    >
      <div className="bg-slate-900/60 border border-white/10 rounded-xl p-4 backdrop-blur-xl shadow-2xl w-72">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 rounded bg-blue-500/20 flex items-center justify-center">
            {isGithub ? <GitBranch className="w-3.5 h-3.5 text-blue-400" /> : <FolderCode className="w-3.5 h-3.5 text-blue-400" />}
          </div>
          <span className="text-xs font-semibold text-slate-400 tracking-wider uppercase">
            CodeMap Workspace
          </span>
        </div>
        
        <div className="mb-3">
          {owner ? (
            <h2 className="text-lg font-bold text-white leading-tight flex flex-col">
              <span className="text-sm font-medium text-slate-400">{owner} /</span>
              <span>{repo}</span>
            </h2>
          ) : (
            <h2 className="text-base font-bold text-white leading-tight truncate">
              {displayName}
            </h2>
          )}
        </div>

        {isGithub && (
          <a 
            href={workspacePath}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-white transition-colors"
          >
            View on GitHub
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </motion.div>
  );
}
