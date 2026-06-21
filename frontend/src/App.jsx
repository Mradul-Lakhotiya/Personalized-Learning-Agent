import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import OnboardingFlow from './components/OnboardingFlow';
import Auth from './components/Auth';
import { Navigation } from './components/Navigation';
import { LearnPage } from './pages/LearnPage';
import { ProgressDashboard } from './pages/ProgressDashboard';
import { useAuth } from './context/AuthContext';
import { supabase } from './supabaseClient';
import { BrainCircuit, LogOut } from 'lucide-react';

function App() {
  const { user, session, signOut } = useAuth();
  // null = loading, false = needs onboarding, true = onboarded
  const [isOnboarded, setIsOnboarded] = useState(null);

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
    <div style={{ width: '100%', maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem', padding: '2rem' }}>

      {/* Header */}
      <header style={{ textAlign: 'center', marginBottom: '1rem', position: 'relative' }}>
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
          <h1 className="gradient-text" style={{ fontSize: '3rem', margin: 0 }}>AI Learning Agent</h1>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', marginTop: 0 }}>
          Your personalized, adaptive, multi-agent tutor.
        </p>
      </header>

      {/* Navigation Menu */}
      <Navigation />

      {/* Main Content Area */}
      <main style={{ width: '100%' }}>
        <Routes>
          <Route path="/" element={<Navigate to="/learn" replace />} />
          <Route path="/learn" element={<LearnPage sessionToken={session?.access_token} />} />
          <Route path="/progress" element={<ProgressDashboard />} />
        </Routes>
      </main>

    </div>
  );
}

export default App;
