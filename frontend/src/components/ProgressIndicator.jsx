import React from 'react';
import { Loader2, Activity, Database, Brain, Network, CheckCircle, FileSearch, HelpCircle } from 'lucide-react';

const getNodeMetadata = (nodeName) => {
  switch (nodeName) {
    case 'Initializing...': return { text: 'Waking up agent...', icon: Activity, color: 'text-cyan-400' };
    case 'profile_builder': return { text: 'Analyzing Learning Profile', icon: Database, color: 'text-blue-400' };
    case 'curriculum_planner': return { text: 'Planning Curriculum', icon: Brain, color: 'text-purple-400' };
    case 'knowledge_assessor': return { text: 'Generating Assessment', icon: HelpCircle, color: 'text-yellow-400' };
    case 'content_delivery': return { text: 'Swarm Orchestration (Fetching Modules)', icon: Network, color: 'text-green-400' };
    case 'practical_worker': return { text: 'Scraping Practical Web Resources', icon: FileSearch, color: 'text-cyan-300' };
    case 'academic_worker': return { text: 'Fetching Arxiv Papers', icon: FileSearch, color: 'text-blue-300' };
    case 'multimedia_worker': return { text: 'Transcribing YouTube Videos', icon: FileSearch, color: 'text-red-400' };
    case 'synthesizer': return { text: 'Synthesizing Swarm Data into Lesson', icon: Brain, color: 'text-purple-500' };
    case 'answer_evaluator': return { text: 'Evaluating Submission', icon: Activity, color: 'text-orange-400' };
    case 'path_rerouter': return { text: 'Calculating Mastery & Routing', icon: Network, color: 'text-indigo-400' };
    case '__interrupt__': return { text: 'Pausing for User Input', icon: CheckCircle, color: 'text-green-500' };
    default: return { text: `Processing ${nodeName}...`, icon: Loader2, color: 'text-gray-400' };
  }
};

export function ProgressIndicator({ isRunning, currentNode }) {
  if (!isRunning && !currentNode) return null;

  const metadata = getNodeMetadata(currentNode);
  const Icon = metadata.icon;

  return (
    <div className="glass-panel" style={{ padding: '1rem 1.5rem', display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
      {isRunning ? (
        <Loader2 className={`animate-spin ${metadata.color}`} size={24} style={{ animation: 'spin 2s linear infinite' }} />
      ) : (
        <CheckCircle className="text-green-500" size={24} />
      )}
      <div>
        <div style={{ fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>
          Agent Status
        </div>
        <div style={{ fontWeight: 500, fontSize: '1.1rem' }} className={metadata.color}>
          {metadata.text}
        </div>
      </div>
      
      {/* Inline styles for the spin animation if Tailwind isn't installed */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin { animation: spin 1s linear infinite; }
        .text-cyan-400 { color: #22d3ee; }
        .text-blue-400 { color: #60a5fa; }
        .text-purple-400 { color: #c084fc; }
        .text-yellow-400 { color: #facc15; }
        .text-green-400 { color: #4ade80; }
        .text-green-500 { color: #22c55e; }
        .text-orange-400 { color: #fb923c; }
        .text-indigo-400 { color: #818cf8; }
        .text-gray-400 { color: #9ca3af; }
      `}</style>
    </div>
  );
}
