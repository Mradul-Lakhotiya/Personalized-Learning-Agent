import React, { useState } from 'react';
import { useAgentStream } from '../hooks/useAgentStream';
import { ProgressIndicator } from '../components/ProgressIndicator';
import { LessonRenderer } from '../components/LessonRenderer';
import { QuestionCard } from '../components/QuestionCard';

export function LearnPage({ sessionToken }) {
  const [threadId] = useState(`thread-${Math.random().toString(36).substring(7)}`);
  const [hasStarted, setHasStarted] = useState(false);
  const { startSession, submitAnswer, isRunning, currentNode, payload, error } = useAgentStream();

  const handleStart = () => {
    setHasStarted(true);
    startSession(sessionToken, threadId);
  };

  const handleSubmit = (answerText) => {
    submitAnswer(sessionToken, threadId, answerText);
  };

  if (!hasStarted) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', marginTop: '4rem' }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1rem' }}>
          Welcome back! Ready to continue learning?
        </p>
        <button
          onClick={handleStart}
          className="glass-panel"
          style={{
            padding: '1rem 3rem', fontSize: '1.25rem', fontWeight: 600,
            color: 'white', background: 'rgba(6, 182, 212, 0.2)',
            border: '1px solid var(--accent-cyan)', cursor: 'pointer',
            transition: 'all 0.3s'
          }}
          onMouseOver={(e) => e.currentTarget.style.background = 'rgba(6, 182, 212, 0.4)'}
          onMouseOut={(e) => e.currentTarget.style.background = 'rgba(6, 182, 212, 0.2)'}
        >
          Start Learning Session
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <ProgressIndicator isRunning={isRunning} currentNode={currentNode} />

      {error && (
        <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#fca5a5', borderRadius: '8px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Loading Skeleton for Swarm Execution */}
      {isRunning && (currentNode === 'content_delivery' || currentNode === 'synthesizer') && !payload?.content_module && (
        <div className="glass-panel p-6 animate-pulse" style={{ marginTop: '1.5rem', marginBottom: '2rem' }}>
          <div className="h-8 bg-slate-700/50 rounded w-1/3 mb-6"></div>
          <div className="h-4 bg-slate-700/50 rounded w-full mb-3"></div>
          <div className="h-4 bg-slate-700/50 rounded w-5/6 mb-3"></div>
          <div className="h-4 bg-slate-700/50 rounded w-4/6 mb-8"></div>
          <div className="h-6 bg-slate-700/50 rounded w-1/4 mb-4"></div>
          <div className="h-4 bg-slate-700/50 rounded w-full mb-2"></div>
          <div className="h-4 bg-slate-700/50 rounded w-3/4 mb-2"></div>
        </div>
      )}

      {payload?.content_module && (
        <LessonRenderer content={payload.content_module} />
      )}

      {payload?.current_question && (
        <QuestionCard
          question={payload.current_question}
          onSubmit={handleSubmit}
          disabled={isRunning}
        />
      )}
    </div>
  );
}
