import { useState } from 'react';
import { Loader2, ChevronRight } from 'lucide-react';

const LABELS = ['None', 'Basic', 'Familiar', 'Good', 'Strong', 'Expert'];

export function SurveyCard({ question, progress, onAnswer, loading }) {
  const [selected, setSelected] = useState(null);

  const handleSubmit = () => {
    if (selected === null) return;
    onAnswer(question.topic, selected);
    setSelected(null);
  };

  if (!question) return null;

  const pct = progress ? Math.round((progress.answered / progress.total) * 100) : 0;

  return (
    <div className="fade-slide-in w-full max-w-[540px]">
      {/* Progress */}
      <div className="mb-6">
        <div className="flex justify-between mb-2">
          <span className="text-xs text-slate-500">Self-Assessment</span>
          <span className="text-xs text-cyan-400">
            {progress?.answered || 0} / {progress?.total || '?'} questions
          </span>
        </div>
        <div className="h-1 bg-white/5 rounded overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-400 to-violet-500 rounded transition-all duration-400"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Question card */}
      <div className="glass-panel p-7">
        <div className="mb-6">
          <div className="text-[0.7rem] text-cyan-400 uppercase tracking-widest font-semibold mb-2">
            Topic: {question.topic}
          </div>
          <p className="text-[1.05rem] text-slate-200 leading-relaxed m-0">
            {question.question}
          </p>
        </div>

        {/* Rating buttons 0–5 */}
        <div className="flex gap-2 justify-center mb-6 flex-wrap">
          {[0, 1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              onClick={() => setSelected(n)}
              className={`survey-rating-btn ${selected === n ? 'selected' : ''}`}
            >
              <span className="flex flex-col items-center leading-tight">
                <span className="text-lg font-bold">{n}</span>
                <span className="text-[0.5rem] opacity-70 tracking-tight">{LABELS[n]}</span>
              </span>
            </button>
          ))}
        </div>

        <button
          onClick={handleSubmit}
          disabled={selected === null || loading}
          className={`w-full py-3 rounded-[10px] text-[0.9rem] font-semibold font-['Outfit'] 
            flex items-center justify-center gap-2 transition-all duration-200
            ${selected === null
              ? 'bg-white/5 text-slate-500 cursor-default border border-transparent'
              : 'bg-cyan-500/20 text-cyan-400 cursor-pointer border border-cyan-500/40 hover:bg-cyan-500/30'
            }
            disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {loading
            ? <Loader2 size={16} className="animate-spin" />
            : <ChevronRight size={16} />
          }
          {loading ? 'Saving...' : 'Next Question'}
        </button>
      </div>
    </div>
  );
}
