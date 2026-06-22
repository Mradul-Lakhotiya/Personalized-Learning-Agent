import { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4000';

import { useAuth } from './context/AuthContext';
import { supabase } from './supabaseClient';
import Auth from './components/Auth';
import OnboardingFlow from './components/OnboardingFlow';
import { Sidebar } from './components/Sidebar';
import { GraphCanvas } from './components/GraphCanvas';
import { NodeDetailPanel } from './components/NodeDetailPanel';
import { useLearningPath } from './hooks/useLearningPath';
import { Loader2 } from 'lucide-react';

function App() {
  const { user, session, signOut } = useAuth();
  const [isOnboarded, setIsOnboarded] = useState(null);
  
  // Local path history
  const [paths, setPaths] = useState([]);
  const [activePath, setActivePath] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  const {
    phase, surveyQuestion,
    curriculumGraph, threadId,
    startNewPath, submitSurveyAnswer, updateGraph, loadCurriculum,
  } = useLearningPath(session?.access_token, user?.id);

  // Check onboarding status and load paths
  useEffect(() => {
    if (!user) return;
    (async () => {
      const { data } = await supabase
        .from('user_profiles')
        .select('learning_goals, background, learning_style')
        .eq('id', user.id)
        .single();
      setIsOnboarded(!!(data && data.background && data.learning_goals?.length > 0));

      // Fetch paths from Node backend
      try {
        const res = await fetch(`${API_BASE_URL}/api/v1/users/${user.id}/conversations`);
        if (res.ok) {
          const json = await res.json();
          setPaths(json.paths || []);
        }
      } catch (e) {
        console.error("Failed to fetch paths:", e);
      }
    })();
  }, [user]);

  // Load selected path from history
  useEffect(() => {
    if (activePath && activePath !== threadId) {
      loadCurriculum(activePath);
    }
  }, [activePath, threadId, loadCurriculum]);

  // Refresh paths when a new graph is ready
  useEffect(() => {
    if (phase === 'graph_ready' && threadId && curriculumGraph && user) {
      // Re-fetch paths from Node backend
      fetch(`${API_BASE_URL}/api/v1/users/${user.id}/conversations`)
        .then(res => res.json())
        .then(json => {
            setPaths(json.paths || []);
            setActivePath(threadId);
        })
        .catch(e => console.error("Failed to refresh paths:", e));
    }
  }, [phase, threadId, curriculumGraph, user]);

  const handleNewPath = () => {
    setActivePath(null);
    setSelectedNode(null);
    // TODO: We need a way to clear the useLearningPath hook state so we can prompt again.
    // For now, this will just rely on the ChatPanel initiating the next call.
  };

  const handleNodeClick = (node) => {
    setSelectedNode(node);
  };

  const handleMarkComplete = (newGraph) => {
    updateGraph(newGraph);
  };

  // Auth / Onboarding gates
  if (!user) return <Auth />;
  if (isOnboarded === null) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }
  if (!isOnboarded) {
    return <OnboardingFlow onComplete={() => setIsOnboarded(true)} />;
  }

  return (
    <div className="bg-background text-on-background font-body-md h-screen overflow-hidden flex">
      {/* 1. Left Panel (Sidebar) */}
      <Sidebar 
        paths={paths}
        activePath={activePath}
        onPathSelect={(p) => setActivePath(p.thread_id)}
        onNewPath={handleNewPath}
        onLogout={signOut}
      />

      {/* Main Content Area */}
      <div className="flex-1 ml-[280px] flex flex-col h-screen relative">
        
        {/* TopNavBar */}
        <header className="w-full h-16 bg-background border-b border-outline-variant z-10 flex-shrink-0">
          <div className="flex justify-between items-center px-gutter w-full max-w-container-max mx-auto h-full">
            <div className="flex items-center gap-4">
              <span className="font-headline-md text-headline-md font-bold text-primary">PathMind AI</span>
            </div>
            <div className="flex items-center gap-4">
              <button className="flex items-center gap-2 hover:bg-surface-container-low px-2 py-1 rounded-lg transition-colors cursor-pointer active:opacity-80">
                <span className="font-label-md text-label-md text-on-surface font-medium hidden sm:block">
                  {user.email}
                </span>
              </button>
            </div>
          </div>
        </header>

        {/* 3-Panel Split Area (Chat vs Graph) */}
        <main className="flex-1 flex overflow-hidden bg-background">
          
          {/* 2. Center Panel (Chat / Interaction) */}
          <div className="w-[400px] border-r border-outline-variant bg-surface-container-lowest flex flex-col z-10 relative shadow-[16px_0_24px_-12px_rgba(0,0,0,0.05)]">
            <div className="px-6 py-4 border-b border-outline-variant bg-surface-container-lowest">
              <h2 className="font-headline-md text-headline-md text-on-surface">Learning Assistant</h2>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
              {/* Chat interactions go here */}
              <div className="bg-surface-container-low p-4 rounded-xl rounded-tl-sm text-on-surface">
                Hi! What would you like to learn today?
              </div>
              
              {/* Temporary placeholder for Survey UI until ChatPanel is built */}
              {(phase === 'survey' || phase === 'starting') && (
                <div className="bg-primary-fixed text-on-primary-fixed p-4 rounded-xl">
                  {phase === 'starting' && !surveyQuestion ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Analyzing your goal...</span>
                    </div>
                  ) : (
                    <div>
                      <p className="font-semibold mb-2">{surveyQuestion?.question}</p>
                      <div className="flex gap-2">
                        {[1,2,3,4,5].map(v => (
                          <button key={v} onClick={() => submitSurveyAnswer(surveyQuestion?.topic, v)} className="bg-surface-container-lowest px-3 py-1 rounded shadow-sm hover:bg-surface-container-low cursor-pointer">
                            {v}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
            {/* Chat Input */}
            <div className="p-4 border-t border-outline-variant bg-surface-container-lowest">
              <input 
                type="text" 
                placeholder="Message AI..." 
                className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-4 py-2 font-body-md focus:outline-none focus:border-primary transition-colors"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.target.value) {
                    startNewPath(e.target.value);
                    e.target.value = '';
                  }
                }}
              />
            </div>
          </div>

          {/* 3. Right Panel (Graph Canvas) */}
          <div className="flex-1 relative overflow-hidden bg-background">
            {phase === 'generating' && (
              <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
                <div className="flex flex-col items-center gap-4">
                  <Loader2 className="w-12 h-12 text-primary animate-spin" />
                  <span className="font-headline-md text-headline-md text-on-surface">Building your curriculum...</span>
                </div>
              </div>
            )}
            
            {(phase === 'graph_ready' || phase === 'idle') && (
              <GraphCanvas
                curriculumGraph={phase === 'graph_ready' ? curriculumGraph : null}
                onNodeClick={handleNodeClick}
              />
            )}
            
            {/* Background Gradient Graphic for depth */}
            <div className="absolute bottom-0 right-0 w-[600px] h-[600px] bg-gradient-to-tl from-primary-fixed-dim/20 to-transparent rounded-tl-full pointer-events-none -z-10"></div>
          </div>

        </main>
      </div>

      <NodeDetailPanel
        node={selectedNode}
        onClose={() => setSelectedNode(null)}
        onMarkComplete={handleMarkComplete}
        sessionToken={session?.access_token}
        userId={user?.id}
        threadId={activePath || threadId}
      />
    </div>
  );
}

export default App;
