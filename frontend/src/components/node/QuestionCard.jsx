import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send } from 'lucide-react';

export function QuestionCard({ question, onSubmit, onSkip, disabled }) {
  const [answer, setAnswer] = useState('');

  if (!question) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!answer.trim()) return;
    onSubmit(answer);
    setAnswer('');
  };

  return (
    <div className="glass-panel p-8 mt-4 w-full max-w-[800px] mx-auto">
      <div className="text-sm uppercase tracking-wider text-violet-400 mb-2">
        Challenge: {question.type.replace('_', ' ')}
      </div>

      <div className="text-xl font-medium mb-6">
        <ReactMarkdown>{question.text}</ReactMarkdown>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {question.type === 'multiple_choice' ? (
          <div className="flex flex-col gap-3">
            {question.options.map((opt, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setAnswer(opt)}
                disabled={disabled}
                className={`flex items-center justify-start px-4 py-3 rounded-lg border text-left text-base
                  transition-all duration-150
                  ${answer === opt
                    ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300'
                    : 'bg-slate-800/50 border-white/[0.08] text-slate-300 hover:border-white/20 hover:text-slate-200'
                  }
                  ${disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                {opt}
              </button>
            ))}
          </div>
        ) : question.type === 'code' ? (
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={disabled}
            placeholder="Write your code here..."
            className="w-full min-h-[150px] p-4 bg-slate-950 text-slate-200 border border-white/[0.08] rounded-lg font-mono resize-y focus:border-cyan-400 outline-none transition-colors"
          />
        ) : (
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={disabled}
            placeholder="Type your answer here..."
            className="w-full min-h-[100px] p-4 bg-black/20 text-slate-200 border border-white/[0.08] rounded-lg resize-y focus:border-cyan-400 outline-none transition-colors"
          />
        )}

        <div className="flex justify-end gap-4 mt-4">
          {onSkip && (
            <button
              type="button"
              onClick={onSkip}
              disabled={disabled}
              className="flex items-center gap-2 px-6 py-3 rounded-lg border border-white/[0.08]
                bg-transparent text-slate-400 font-semibold transition-all duration-200
                hover:bg-white/5 hover:text-slate-300
                disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              Skip
            </button>
          )}

          <button
            type="submit"
            disabled={disabled || !answer.trim()}
            className="flex items-center gap-2 px-6 py-3 rounded-lg border-none
              bg-violet-500 text-white font-semibold transition-all duration-200
              hover:bg-violet-600 hover:shadow-lg hover:shadow-violet-500/20
              disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            Submit <Send size={18} />
          </button>
        </div>
      </form>
    </div>
  );
}
