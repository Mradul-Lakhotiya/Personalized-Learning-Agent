import ReactMarkdown from 'react-markdown';

export function LessonRenderer({ content }) {
  if (!content) return null;

  return (
    <div className="glass-panel" style={{ padding: '2rem', marginTop: '1.5rem', marginBottom: '2rem' }}>
      <div className="lesson-content">
        <ReactMarkdown
          components={{
            code: ({inline, ...props}) => 
              inline ? 
                <code style={{ background: 'rgba(255,255,255,0.1)', padding: '0.1rem 0.3rem', borderRadius: '4px', color: 'var(--accent-purple)' }} {...props} /> :
                <code style={{ display: 'block', background: '#0f172a', padding: '1rem', borderRadius: '8px', overflowX: 'auto', marginBottom: '1rem', border: '1px solid var(--glass-border)' }} {...props} />,
            blockquote: ({ ...props}) => <blockquote style={{ borderLeft: '4px solid var(--accent-purple)', paddingLeft: '1rem', color: 'var(--text-secondary)', fontStyle: 'italic', margin: '1rem 0' }} {...props} />
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
