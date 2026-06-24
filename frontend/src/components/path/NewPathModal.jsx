import { useState } from 'react';
import { X, Loader2, BrainCircuit, ArrowRight } from 'lucide-react';

const QUICK_STARTS = [
  'Machine Learning basics',
  'Data Structures & Algorithms',
  'Web Development with React',
  'Python for beginners',
  'System Design',
];

export function NewPathModal({ onClose, onSubmit, loading }) {
  const [goal, setGoal] = useState('');

  const handleSubmit = () => {
    if (!goal.trim() || loading) return;
    onSubmit(goal.trim());
  };

  return (
    <div
      className="modal-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="modal-card fade-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-white/[0.07]">
          <div className="flex items-center gap-3">
            <BrainCircuit size={24} className="text-cyan-400" />
            <div>
              <h2 className="text-[1.1rem] font-bold m-0">Create New Learning Path</h2>
              <p className="text-[0.8rem] text-slate-500 m-0">Describe what you want to master</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="bg-transparent border-none cursor-pointer text-slate-500 hover:text-slate-300 transition-colors p-1"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && e.metaKey && handleSubmit()}
            placeholder={
              'E.g. I want to learn Machine Learning from scratch…\n' +
              'E.g. I want to master Data Structures and Algorithms…\n' +
              'E.g. I want to build full-stack apps with React and Node.js…'
            }
            autoFocus
            className="w-full h-[130px] p-4 bg-white/[0.04] border border-white/10 rounded-xl
              text-slate-200 text-[0.95rem] font-['Outfit'] resize-none outline-none leading-relaxed
              focus:border-cyan-400 transition-colors duration-200"
          />

          {/* Quick start suggestions */}
          <div className="mt-3 mb-6">
            <p className="text-[0.75rem] text-slate-500 mb-2">Quick starts:</p>
            <div className="flex flex-wrap gap-1.5">
              {QUICK_STARTS.map((s) => (
                <button
                  key={s}
                  onClick={() => setGoal(s)}
                  className={`px-2.5 py-1 rounded-md text-[0.75rem] font-['Outfit'] cursor-pointer
                    border transition-all duration-150
                    ${goal === s
                      ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-400'
                      : 'bg-white/[0.04] border-white/[0.08] text-slate-500 hover:border-white/20 hover:text-slate-400'
                    }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!goal.trim() || loading}
            className={`w-full py-[0.9rem] rounded-xl text-base font-semibold font-['Outfit']
              flex items-center justify-center gap-2 transition-all duration-200
              ${!goal.trim()
                ? 'bg-white/[0.05] text-slate-500 cursor-default border-none'
                : 'bg-gradient-to-br from-cyan-500/30 to-violet-500/30 text-slate-200 border border-cyan-500/30 cursor-pointer hover:from-cyan-500/40 hover:to-violet-500/40'
              }
              disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {loading
              ? <><Loader2 size={18} className="animate-spin" /> Generating your path...</>
              : <><ArrowRight size={18} /> Generate Learning Path</>
            }
          </button>
          <p className="text-center text-[0.72rem] text-slate-700 mt-3">
            We'll ask a few quick questions to personalize your path.
          </p>
        </div>
      </div>
    </div>
  );
}
