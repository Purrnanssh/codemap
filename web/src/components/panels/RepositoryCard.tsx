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
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 bg-slate-900/80 border border-white/10 rounded-full px-4 py-1.5 backdrop-blur-xl shadow-lg"
    >
      <div className="flex items-center gap-1.5">
        {isGithub ? <GitBranch className="w-3.5 h-3.5 text-blue-400" /> : <FolderCode className="w-3.5 h-3.5 text-blue-400" />}
        <span className="text-xs font-semibold text-white tracking-wide">
          {displayName}
        </span>
      </div>

      {isGithub && (
        <>
          <div className="w-1 h-1 rounded-full bg-slate-600"></div>
          <a 
            href={workspacePath}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-white transition-colors uppercase tracking-wider"
          >
            View GitHub
            <ExternalLink className="w-3 h-3" />
          </a>
        </>
      )}
    </motion.div>
  );
}
