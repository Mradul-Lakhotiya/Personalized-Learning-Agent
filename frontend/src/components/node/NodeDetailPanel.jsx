import { useState, useEffect } from 'react';
import { fetchNodeDetails, streamNodeGeneration, completeNode } from '../../services/pathApi';
import { QuestionCard } from './QuestionCard';

const DIFF_LABEL = ['', 'Beginner', 'Easy', 'Medium', 'Hard', 'Expert'];

export function NodeDetailPanel({ node, onClose, onMarkComplete, sessionToken, userId, threadId }) {
  const [completing, setCompleting]         = useState(false);
  const [completed, setCompleted]           = useState(false);
  const [resources, setResources]           = useState(node?.resources || []);
  const [questions, setQuestions]           = useState([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [needsGeneration, setNeedsGeneration]   = useState(false);
  const [generationStatus, setGenerationStatus] = useState('');
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  const handleGenerateResources = async () => {
    setLoadingResources(true);
    setNeedsGeneration(false);
    setGenerationStatus('Triggering generation...');
    try {
      const response = await streamNodeGeneration(userId, threadId, node.id, sessionToken);

      if (!response.ok) {
        setGenerationStatus('Generation failed. Please try again.');
        setLoadingResources(false);
        setNeedsGeneration(true);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const messages = buffer.split('\n\n');
        buffer = messages.pop() || '';

        for (const msg of messages) {
          if (!msg.startsWith('data: ')) continue;
          try {
            const eventData = JSON.parse(msg.replace('data: ', '').trim());
            if (eventData.type === 'status') {
              setGenerationStatus(eventData.message);
            } else if (eventData.type === 'ready') {
              try {
                const data = await fetchNodeDetails(userId, threadId, node.id, sessionToken);
                setResources(data.resources_cached || []);
                setQuestions(data.questions_cached || []);
              } catch (e) {
                console.error('Failed to fetch after generation', e);
              }
              setLoadingResources(false);
              return;
            } else if (eventData.type === 'error') {
              setGenerationStatus(`Error: ${eventData.message}`);
              setLoadingResources(false);
              setNeedsGeneration(true);
              return;
            }
          } catch { /* ignore parse errors */ }
        }
      }
    } catch (e) {
      console.error('Failed to trigger generation:', e);
      setGenerationStatus('Failed to connect to server.');
      setLoadingResources(false);
      setNeedsGeneration(true);
    }
  };

  useEffect(() => {
    if (!node) return;
    setCompleted(node.status === 'completed');
    setResources(node.resources || []);
    setQuestions([]);
    setCurrentQuestionIndex(0);

    const fetchOnly = async () => {
      setLoadingResources(true);
      try {
        const data = await fetchNodeDetails(userId, threadId, node.id, sessionToken);
        if (data && (data.resources_cached || data.questions_cached)) {
          setResources(data.resources_cached || []);
          setQuestions(data.questions_cached || []);
          setLoadingResources(false);
          setNeedsGeneration(false);
          return;
        }
      } catch (e) {
        console.error('Failed to fetch from Node API', e);
      }
      setLoadingResources(false);
      if (node.is_major) setNeedsGeneration(true);
    };

    fetchOnly();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [node?.id, node?.status, sessionToken, userId, threadId]);

  if (!node) return null;

  const handleComplete = async () => {
    if (completed || completing) return;
    setCompleting(true);
    try {
      const data = await completeNode(userId, threadId, node.id, sessionToken);
      if (data.success) {
        setCompleted(true);
        onMarkComplete?.(data.curriculum_graph);
      }
    } catch (e) {
      console.error('Failed to complete node:', e);
    } finally {
      setCompleting(false);
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 bg-on-background/20 backdrop-blur-sm z-40"
        onClick={onClose}
      />
      <div className="fixed top-0 right-0 h-full w-panel-width bg-surface-container-lowest border-l border-outline-variant shadow-[16px_0_24px_-12px_rgba(0,0,0,0.15)] z-50 flex flex-col transform transition-transform duration-300">

        {/* Header */}
        <div className="px-6 py-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-lowest">
          <h2 className="font-headline-md text-headline-md text-on-surface">Module Details</h2>
          <button
            onClick={onClose}
            className="text-on-surface-variant hover:bg-surface-container-low p-2 rounded-full transition-colors flex items-center justify-center cursor-pointer"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6 bg-surface-container-lowest space-y-6">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-secondary-container text-on-secondary-container font-label-sm text-label-sm mb-3">
              <span className="material-symbols-outlined text-[14px]">
                {completed ? 'check_circle' : (node.status === 'in_progress' ? 'play_circle' : 'lock')}
              </span>
              {completed ? 'Completed' : (node.status === 'locked' ? 'Locked' : 'Available')}
            </div>

            <h1 className="font-headline-lg text-headline-lg text-on-surface mb-2">{node.title}</h1>
            <p className="font-body-md text-body-md text-on-surface-variant">
              {node.description || 'An important topic in your learning journey.'}
            </p>
          </div>

          <div className="flex gap-4">
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">Difficulty</span>
              <span className="font-label-md text-label-md text-on-surface">{DIFF_LABEL[node.difficulty] || 'Beginner'}</span>
            </div>
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">Time</span>
              <span className="font-label-md text-label-md text-on-surface">~{node.estimated_minutes || 30} mins</span>
            </div>
          </div>

          {/* Resources */}
          {resources && resources.length > 0 ? (
            <div>
              <h3 className="font-label-md text-label-md text-on-surface font-semibold mb-3">Curated Resources</h3>
              <ul className="space-y-3">
                {resources.map((r, i) => (
                  <li key={i}>
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start gap-3 p-3 rounded-lg border border-outline-variant hover:bg-surface-container-low transition-colors group"
                    >
                      <span className="material-symbols-outlined text-primary text-[20px] mt-0.5 group-hover:scale-110 transition-transform">
                        {r.type === 'video' ? 'play_circle' : (r.type === 'academic' ? 'school' : 'article')}
                      </span>
                      <div>
                        <span className="block font-label-md text-label-md text-on-surface">{r.title}</span>
                        <span className="block font-label-sm text-label-sm text-on-surface-variant truncate w-[280px]">{r.url}</span>
                      </div>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : node.is_major && needsGeneration ? (
            <div className="p-5 bg-surface-container border border-outline-variant rounded-xl text-center shadow-sm">
              <h3 className="font-label-lg text-label-lg text-on-surface font-semibold mb-2">Deep Dive Available</h3>
              <p className="font-label-sm text-label-sm text-on-surface-variant mb-5">
                Click below to trigger our AI Swarm. It will scour the internet to curate resources
                and synthesize custom quiz questions specifically for {node.title}.
              </p>
              <button
                onClick={handleGenerateResources}
                className="px-6 py-2.5 bg-primary text-on-primary rounded-full font-label-md hover:bg-primary-container hover:text-on-primary-container transition-colors cursor-pointer shadow-sm flex items-center justify-center gap-2 mx-auto"
              >
                <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
                Generate Resources
              </button>
            </div>
          ) : node.is_major && loadingResources ? (
            <div className="p-4 bg-primary-fixed border border-primary-fixed-dim rounded-xl shadow-sm">
              <div className="flex items-center gap-2 mb-1 text-on-primary-fixed">
                <span className="material-symbols-outlined text-[18px] animate-pulse">auto_awesome</span>
                <span className="font-label-md text-label-md font-semibold animate-pulse">Generating...</span>
              </div>
              <p className="font-label-sm text-label-sm text-on-primary-fixed-variant">
                {generationStatus || 'Our AI agents are currently browsing the web to curate the best learning materials for this major topic.'}
              </p>
            </div>
          ) : null}

          {/* Knowledge Check */}
          {questions && questions.length > 0 && (
            <div className="mt-6 border-t border-outline-variant pt-6">
              <h3 className="font-label-md text-label-md text-on-surface font-semibold mb-3 flex justify-between items-center">
                <span>Knowledge Check</span>
                <span className="text-primary text-sm font-normal">
                  Question {currentQuestionIndex + 1} of {questions.length}
                </span>
              </h3>

              <div className="relative overflow-hidden min-h-[300px]">
                {questions.map((q, idx) => {
                  const isActive = idx === currentQuestionIndex;
                  const isPast   = idx < currentQuestionIndex;
                  return (
                    <div
                      key={idx}
                      className={`absolute inset-0 w-full transition-all duration-300 ease-in-out ${
                        isActive ? 'translate-x-0 opacity-100' :
                        isPast   ? '-translate-x-full opacity-0 pointer-events-none' :
                                   'translate-x-full opacity-0 pointer-events-none'
                      }`}
                    >
                      <QuestionCard
                        question={q}
                        onSubmit={() => {
                          if (currentQuestionIndex < questions.length - 1)
                            setCurrentQuestionIndex(prev => prev + 1);
                        }}
                        onSkip={() => {
                          if (currentQuestionIndex < questions.length - 1)
                            setCurrentQuestionIndex(prev => prev + 1);
                        }}
                        disabled={completing}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Prerequisites */}
          {node.prerequisites && node.prerequisites.length > 0 && (
            <div>
              <h3 className="font-label-md text-label-md text-on-surface font-semibold mb-3">Prerequisites</h3>
              <div className="flex flex-wrap gap-2">
                {node.prerequisites.map(p => (
                  <span key={p} className="px-3 py-1 bg-surface-container-high text-on-surface rounded-full font-label-sm text-label-sm border border-outline-variant">
                    {p.replace(/-/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer CTA */}
        <div className="p-6 border-t border-outline-variant bg-surface-container-lowest">
          {node.status === 'locked' ? (
            <div className="text-center font-label-md text-label-md text-on-surface-variant">
              🔒 Complete prerequisites to unlock
            </div>
          ) : (
            <button
              onClick={handleComplete}
              disabled={completed || completing}
              className={`w-full py-3 px-4 rounded-lg font-label-md text-label-md font-semibold transition-colors shadow-sm flex items-center justify-center gap-2 ${
                completed
                  ? 'bg-[#D1FAE5] text-[#065F46]'
                  : 'bg-primary text-on-primary hover:bg-primary-container hover:text-on-primary-container cursor-pointer'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">
                {completed ? 'check_circle' : 'check'}
              </span>
              {completed ? 'Completed' : (completing ? 'Saving...' : 'Mark as Completed')}
            </button>
          )}
        </div>
      </div>
    </>
  );
}
