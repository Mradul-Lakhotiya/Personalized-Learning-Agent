import { useState } from 'react';
import { Loader2, ChevronRight } from 'lucide-react';

const LABELS = ['0\nNone', '1\nBasic', '2\nFamiliar', '3\nGood', '4\nStrong', '5\nExpert'];

export function SurveyCard({ question, progress, onAnswer, loading }) {
  const [selected, setSelected] = useState(null);

  const handleSubmit = () => {
    if (selected === null) return;
    onAnswer(question.topic, selected);
    setSelected(null);
  };

  if (!question) return null;

  const pct = progress
    ? Math.round((progress.answered / progress.total) * 100)
    : 0;

  return (
    <div className="fade-slide-in" style={{ width: '100%', maxWidth: 540 }}>
      {/* Progress */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Self-Assessment</span>
          <span style={{ fontSize: '0.75rem', color: '#06b6d4' }}>
            {progress?.answered || 0} / {progress?.total || '?'} questions
          </span>
        </div>
        <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 4, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${pct}%`,
            background: 'linear-gradient(90deg, #06b6d4, #8b5cf6)',
            borderRadius: 4,
            transition: 'width 0.4s ease',
          }} />
        </div>
      </div>

      {/* Question card */}
      <div className="glass-panel" style={{ padding: '1.75rem' }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ fontSize: '0.7rem', color: '#06b6d4', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.6rem', fontWeight: 600 }}>
            Topic: {question.topic}
          </div>
          <p style={{ fontSize: '1.05rem', color: '#e2e8f0', lineHeight: 1.55, margin: 0 }}>
            {question.question}
          </p>
        </div>

        {/* Rating buttons 0–5 */}
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          {[0, 1, 2, 3, 4, 5].map(n => (
            <button
              key={n}
              className={`survey-rating-btn ${selected === n ? 'selected' : ''}`}
              onClick={() => setSelected(n)}
            >
              <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', lineHeight: 1.1 }}>
                <span style={{ fontSize: '1.1rem', fontWeight: 700 }}>{n}</span>
                <span style={{ fontSize: '0.5rem', opacity: 0.7, letterSpacing: '0.02em' }}>
                  {LABELS[n].split('\n')[1]}
                </span>
              </span>
            </button>
          ))}
        </div>

        <button
          onClick={handleSubmit}
          disabled={selected === null || loading}
          style={{
            width: '100%',
            padding: '0.8rem',
            borderRadius: '10px',
            border: 'none',
            background: selected === null ? 'rgba(255,255,255,0.06)' : 'rgba(6,182,212,0.2)',
            color: selected === null ? '#475569' : '#06b6d4',
            borderColor: selected === null ? 'transparent' : 'rgba(6,182,212,0.4)',
            borderWidth: 1,
            borderStyle: 'solid',
            fontSize: '0.9rem',
            fontWeight: 600,
            fontFamily: 'Outfit, sans-serif',
            cursor: selected === null ? 'default' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
            transition: 'all 0.2s',
          }}
        >
          {loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <ChevronRight size={16} />}
          {loading ? 'Saving...' : 'Next Question'}
        </button>
      </div>
    </div>
  );
}
