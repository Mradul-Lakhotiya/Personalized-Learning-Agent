import React, { useState, useEffect } from 'react';
import { useAgentStream } from './hooks/useAgentStream';
import { ProgressIndicator } from './components/ProgressIndicator';
import { LessonRenderer } from './components/LessonRenderer';
import { QuestionCard } from './components/QuestionCard';
import OnboardingFlow from './components/OnboardingFlow';
import Auth from './components/Auth';
import { useAuth } from './context/AuthContext';
import { supabase } from './supabaseClient';
import { BrainCircuit, LogOut } from 'lucide-react';

function App() {
  const { user, session, signOut } = useAuth();
  const [threadId] = useState(`thread-${Math.random().toString(36).substring(7)}`);
  const [hasStarted, setHasStarted] = useState(false);
  // null = loading, false = needs onboarding, true = onboarded
  const [isOnboarded, setIsOnboarded] = useState(null);

  const { startSession, submitAnswer, isRunning, currentNode, payload, error } = useAgentStream();

  // Check if the user has already completed onboarding
  useEffect(() => {
    if (!user) return;
    (async () => {
      const { data } = await supabase
        .from('user_profiles')
        .select('learning_goals, background, learning_style')
        .eq('id', user.id)
        .single();

      // Consider onboarded if they have at least a learning goal and background set
      const done = data && data.background && data.learning_goals?.length > 0;
      setIsOnboarded(!!done);
    })();
  }, [user]);

  const handleStart = () => {
    setHasStarted(true);
    startSession(session?.access_token, threadId);
  };

  const handleSubmit = (answerText) => {
    submitAnswer(session?.access_token, threadId, answerText);
  };

  // ── Not logged in ─────────────────────────────────────────────────────────
  if (!user) {
    return <Auth />;
  }

  // ── Loading onboarding status ─────────────────────────────────────────────
  if (isOnboarded === null) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-secondary)', fontSize: '1rem' }}>Loading your profile...</div>
      </div>
    );
  }

  // ── New user: show onboarding first ──────────────────────────────────────
  if (!isOnboarded) {
    return <OnboardingFlow onComplete={() => setIsOnboarded(true)} />;
  }

  // ── Returning user: main learning interface ───────────────────────────────
  return (
    <div style={{ width: '100%', maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>

      {/* Header */}
      <header style={{ textAlign: 'center', marginBottom: '2rem', position: 'relative' }}>
        <div style={{ position: 'absolute', top: 0, right: 0 }}>
          <button
            onClick={signOut}
            className="flex items-center gap-2 text-slate-400 hover:text-red-400 transition-colors"
          >
            <LogOut size={20} />
            <span className="text-sm font-medium">Sign Out</span>
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <BrainCircuit size={48} className="text-cyan-400" />
          <h1 className="gradient-text" style={{ fontSize: '3rem' }}>AI Learning Agent</h1>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem' }}>
          Your personalized, adaptive, multi-agent tutor.
        </p>
      </header>

      {/* Main Content Area */}
      <main style={{ width: '100%' }}>
        {!hasStarted ? (
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
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

            <ProgressIndicator isRunning={isRunning} currentNode={currentNode} />

            {error && (
              <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#fca5a5', borderRadius: '8px' }}>
                <strong>Error:</strong> {error}
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
        )}
      </main>

    </div>
  );
}

export default App;
