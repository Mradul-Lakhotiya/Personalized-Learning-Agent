import React from 'react';
import ReactMarkdown from 'react-markdown';

export function LessonRenderer({ content }) {
  if (!content) return null;

  return (
    <div className="glass-panel" style={{ padding: '2rem', marginTop: '1.5rem', marginBottom: '2rem' }}>
      <div className="lesson-content">
        <ReactMarkdown
          components={{
            h1: ({node, ...props}) => <h1 className="gradient-text" style={{ fontSize: '2rem', marginBottom: '1rem' }} {...props} />,
            h2: ({node, ...props}) => <h2 style={{ fontSize: '1.5rem', marginTop: '1.5rem', marginBottom: '0.75rem', color: 'var(--accent-cyan)' }} {...props} />,
            h3: ({node, ...props}) => <h3 style={{ fontSize: '1.25rem', marginTop: '1rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }} {...props} />,
            p: ({node, ...props}) => <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }} {...props} />,
            ul: ({node, ...props}) => <ul style={{ marginLeft: '1.5rem', marginBottom: '1rem', color: 'var(--text-secondary)' }} {...props} />,
            ol: ({node, ...props}) => <ol style={{ marginLeft: '1.5rem', marginBottom: '1rem', color: 'var(--text-secondary)' }} {...props} />,
            li: ({node, ...props}) => <li style={{ marginBottom: '0.25rem' }} {...props} />,
            code: ({node, inline, ...props}) => 
              inline ? 
                <code style={{ background: 'rgba(255,255,255,0.1)', padding: '0.1rem 0.3rem', borderRadius: '4px', color: 'var(--accent-purple)' }} {...props} /> :
                <code style={{ display: 'block', background: '#0f172a', padding: '1rem', borderRadius: '8px', overflowX: 'auto', marginBottom: '1rem', border: '1px solid var(--glass-border)' }} {...props} />,
            blockquote: ({node, ...props}) => <blockquote style={{ borderLeft: '4px solid var(--accent-purple)', paddingLeft: '1rem', color: 'var(--text-secondary)', fontStyle: 'italic', margin: '1rem 0' }} {...props} />
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
