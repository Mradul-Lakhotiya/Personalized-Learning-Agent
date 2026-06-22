import { Clock, Plus } from 'lucide-react';

export function PathHistorySidebar({ paths = [], activePath, onPathSelect, onNewPath }) {
  return (
    <div className="path-sidebar">
      {/* Header */}
      <div className="path-sidebar-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Map size={16} color="#06b6d4" />
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8' }}>
            Learning Paths
          </span>
        </div>
        <button
          id="new-path-btn"
          onClick={onNewPath}
          title="Create new learning path"
          style={{
            width: 28, height: 28,
            borderRadius: '8px',
            border: '1px solid rgba(6,182,212,0.4)',
            background: 'rgba(6,182,212,0.1)',
            color: '#06b6d4',
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.15s',
          }}
          onMouseOver={e => e.currentTarget.style.background = 'rgba(6,182,212,0.2)'}
          onMouseOut={e => e.currentTarget.style.background = 'rgba(6,182,212,0.1)'}
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Path list */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {paths.length === 0 ? (
          <div style={{
            padding: '2rem 1rem',
            textAlign: 'center',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem',
          }}>
            <div style={{ fontSize: '2rem' }}>🗺️</div>
            <p style={{ fontSize: '0.8rem', color: '#475569', lineHeight: 1.5 }}>
              No paths yet.<br />
              Click <strong style={{ color: '#06b6d4' }}>+</strong> to create your first one.
            </p>
          </div>
        ) : (
          paths.map(path => (
            <button
              key={path.thread_id}
              className={`path-item ${activePath === path.thread_id ? 'active' : ''}`}
              onClick={() => onPathSelect(path)}
              style={{
                width: '100%', border: 'none', background: 'none',
                textAlign: 'left', cursor: 'pointer', fontFamily: 'Outfit, sans-serif',
              }}
            >
              <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '0.25rem', lineHeight: 1.3 }}>
                {path.learning_goal || 'Unnamed Path'}
              </div>
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <span style={{ fontSize: '0.7rem', color: '#475569' }}>
                  {path.completed_count || 0}/{path.node_count || 0} nodes
                </span>
                {path.created_at && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: '0.68rem', color: '#334155' }}>
                    <Clock size={9} />
                    {new Date(path.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
