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
    <div className="glass-panel" style={{ padding: '2rem', marginTop: '1rem', width: '100%', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ marginBottom: '0.5rem', fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-purple)' }}>
        Challenge: {question.type.replace('_', ' ')}
      </div>
      
      <div style={{ fontSize: '1.25rem', fontWeight: 500, marginBottom: '1.5rem' }}>
        <ReactMarkdown>{question.text}</ReactMarkdown>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {question.type === 'multiple_choice' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {question.options.map((opt, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setAnswer(opt)}
                disabled={disabled}
                className="transition-all"
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
                  padding: '1rem',
                  background: answer === opt ? 'rgba(6, 182, 212, 0.2)' : 'rgba(30, 41, 59, 0.5)',
                  border: answer === opt ? '1px solid #06b6d4' : '1px solid var(--glass-border)',
                  borderRadius: '8px',
                  color: answer === opt ? '#22d3ee' : '#cbd5e1',
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  opacity: disabled ? 0.6 : 1,
                  textAlign: 'left',
                  fontSize: '1rem'
                }}
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
            style={{ 
              width: '100%', minHeight: '150px', padding: '1rem', 
              background: '#0f172a', color: '#e2e8f0', 
              border: '1px solid var(--glass-border)', borderRadius: '8px',
              fontFamily: 'monospace', resize: 'vertical'
            }}
          />
        ) : (
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={disabled}
            placeholder="Type your answer here..."
            style={{ 
              width: '100%', minHeight: '100px', padding: '1rem', 
              background: 'rgba(0,0,0,0.2)', color: 'var(--text-primary)', 
              border: '1px solid var(--glass-border)', borderRadius: '8px',
              resize: 'vertical'
            }}
          />
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
          {onSkip && (
            <button 
              type="button"
              onClick={onSkip}
              disabled={disabled}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                background: 'transparent',
                color: 'var(--text-secondary)',
                border: '1px solid var(--glass-border)',
                borderRadius: '8px',
                fontWeight: 600,
                cursor: disabled ? 'not-allowed' : 'pointer',
                opacity: disabled ? 0.5 : 1,
                transition: 'opacity 0.2s, background 0.2s'
              }}
              onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
              onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
            >
              Skip
            </button>
          )}

          <button 
            type="submit" 
            disabled={disabled || !answer.trim()}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.75rem 1.5rem',
              background: 'var(--accent-purple)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontWeight: 600,
              cursor: (disabled || !answer.trim()) ? 'not-allowed' : 'pointer',
              opacity: (disabled || !answer.trim()) ? 0.5 : 1,
              transition: 'opacity 0.2s'
            }}
          >
            Submit <Send size={18} />
          </button>
        </div>
      </form>
    </div>
  );
}
