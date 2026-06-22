import { useState } from 'react';
import { X, Loader2, BrainCircuit, ArrowRight } from 'lucide-react';

export function NewPathModal({ onClose, onSubmit, loading }) {
  const [goal, setGoal] = useState('');

  const handleSubmit = () => {
    if (!goal.trim() || loading) return;
    onSubmit(goal.trim());
  };

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-card fade-slide-in">
        {/* Header */}
        <div style={{
          padding: '1.5rem 1.5rem 1rem',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <BrainCircuit size={24} color="#06b6d4" />
            <div>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Create New Learning Path</h2>
              <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>
                Describe what you want to master
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '1.5rem' }}>
          <textarea
            value={goal}
            onChange={e => setGoal(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && e.metaKey && handleSubmit()}
            placeholder="E.g. I want to learn Machine Learning from scratch…&#10;E.g. I want to master Data Structures and Algorithms…&#10;E.g. I want to build full-stack apps with React and Node.js…"
            autoFocus
            style={{
              width: '100%',
              height: '130px',
              padding: '1rem',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '12px',
              color: '#e2e8f0',
              fontSize: '0.95rem',
              fontFamily: 'Outfit, sans-serif',
              resize: 'none',
              outline: 'none',
              lineHeight: 1.6,
              transition: 'border-color 0.2s',
            }}
            onFocus={e => e.target.style.borderColor = '#06b6d4'}
            onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
          />

          {/* Suggestions */}
          <div style={{ marginTop: '0.75rem', marginBottom: '1.5rem' }}>
            <p style={{ fontSize: '0.75rem', color: '#475569', marginBottom: '0.5rem' }}>Quick starts:</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
              {[
                'Machine Learning basics',
                'Data Structures & Algorithms',
                'Web Development with React',
                'Python for beginners',
                'System Design',
              ].map(s => (
                <button
                  key={s}
                  onClick={() => setGoal(s)}
                  style={{
                    padding: '4px 10px',
                    background: goal === s ? 'rgba(6,182,212,0.15)' : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${goal === s ? 'rgba(6,182,212,0.4)' : 'rgba(255,255,255,0.08)'}`,
                    borderRadius: '6px',
                    color: goal === s ? '#06b6d4' : '#64748b',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    fontFamily: 'Outfit, sans-serif',
                    transition: 'all 0.15s',
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!goal.trim() || loading}
            style={{
              width: '100%',
              padding: '0.9rem',
              borderRadius: '12px',
              background: !goal.trim()
                ? 'rgba(255,255,255,0.05)'
                : 'linear-gradient(135deg, rgba(6,182,212,0.3), rgba(139,92,246,0.3))',
              color: !goal.trim() ? '#475569' : '#e2e8f0',
              fontSize: '1rem',
              fontWeight: 600,
              fontFamily: 'Outfit, sans-serif',
              cursor: !goal.trim() || loading ? 'default' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
              border: !goal.trim() ? 'none' : '1px solid rgba(6,182,212,0.3)',
              transition: 'all 0.2s',
            }}
          >
            {loading
              ? <><Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> Generating your path...</>
              : <><ArrowRight size={18} /> Generate Learning Path</>
            }
          </button>
          <p style={{ textAlign: 'center', fontSize: '0.72rem', color: '#334155', marginTop: '0.75rem' }}>
            We'll ask a few quick questions to personalize your path.
          </p>
        </div>
      </div>
    </div>
  );
}
