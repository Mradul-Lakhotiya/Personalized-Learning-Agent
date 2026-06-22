import { useState, useCallback, useRef } from 'react';

const AI_API = `${import.meta.env.VITE_AI_API_BASE_URL || 'http://localhost:8000'}/api/v1`;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4000';

export function useLearningPath(sessionToken, userId) {
  const NODE_API = `${API_BASE_URL}/api/v1/users/${userId}/conversations`;
  const [phase, setPhase] = useState('idle');           // idle | starting | survey | generating | graph_ready | error
  const [surveyQuestion, setSurveyQuestion] = useState(null);
  const [surveyProgress, setSurveyProgress] = useState(null);
  const [curriculumGraph, setCurriculumGraph] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const threadIdRef = useRef(null);

  // getHeaders reads sessionToken at call-time — fresh token on every fetch
  const getHeaders = useCallback(() => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${sessionToken}`,
  }), [sessionToken]);

  // ── SSE stream reader helper ──────────────────────────────────────────────
  const readSSEStream = async (response, onPayload) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const messages = buffer.split('\n\n');
        buffer = messages.pop() || '';

        for (const msg of messages) {
          if (!msg.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(msg.replace('data: ', '').trim());
            onPayload(data);
          } catch {
            // ignore parse errors
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  };

  // ── Start a new session (sends learning goal) ─────────────────────────────
  const startNewPath = useCallback(async (learningGoal) => {
    setLoading(true);
    setError(null);
    setPhase('starting');

    const newThreadId = `thread-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    threadIdRef.current = newThreadId;
    setThreadId(newThreadId);

    try {
      const response = await fetch(`${AI_API}/agent/start`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ thread_id: threadIdRef.current, initial_prompt: learningGoal }),
      });

      await readSSEStream(response, (data) => {
        if (data.type === 'execution_complete') {
          const p = data.payload;
          if (p?.phase === 'onboarding' && p?.survey_question) {
            setSurveyQuestion(p.survey_question);
            setSurveyProgress(p.survey_progress);
            setPhase('survey');
          } else if (p?.phase === 'graph_ready' && p?.curriculum_graph) {
            setCurriculumGraph(p.curriculum_graph);
            setPhase('graph_ready');
          }
        } else if (data.type === 'fatal_error') {
          setError(data.message);
          setPhase('error');
        }
      });
    } catch (e) {
      setError(e.message);
      setPhase('error');
    } finally {
      setLoading(false);
    }
  }, [getHeaders]);

  // ── Generate curriculum after survey ─────────────────────────────────────
  const generateCurriculum = useCallback(async () => {
    if (!threadIdRef.current) return;
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${AI_API}/agent/generate-curriculum`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ thread_id: threadIdRef.current }),
      });

      await readSSEStream(response, (data) => {
        if (data.type === 'execution_complete') {
          const p = data.payload;
          if (p?.phase === 'graph_ready' && p?.curriculum_graph) {
            setCurriculumGraph(p.curriculum_graph);
            setPhase('graph_ready');
          }
        } else if (data.type === 'fatal_error') {
          setError(data.message);
          setPhase('error');
        }
      });
    } catch (e) {
      setError(e.message);
      setPhase('error');
    } finally {
      setLoading(false);
    }
  }, [getHeaders]);

  // ── Submit one survey answer ──────────────────────────────────────────────
  const submitSurveyAnswer = useCallback(async (topic, rating) => {
    if (!threadIdRef.current) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${AI_API}/agent/survey-answer`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ thread_id: threadIdRef.current, topic, rating }),
      });
      const data = await res.json();

      if (data.survey_complete) {
        // All answers collected — trigger graph generation
        setPhase('generating');
        setSurveyQuestion(null);
        await generateCurriculum();
      } else if (data.next_question) {
        setSurveyQuestion(data.next_question);
        setSurveyProgress(data.progress);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [getHeaders, generateCurriculum]);

  // ── Load curriculum for existing session ─────────────────────────────────
  const loadCurriculum = useCallback(async (existingThreadId) => {
    setLoading(true);
    setError(null);
    threadIdRef.current = existingThreadId;
    setThreadId(existingThreadId);

    try {
      if (!userId) {
          throw new Error("User ID is required to load curriculum");
      }
      const response = await fetch(`${NODE_API}/${existingThreadId}`, {
        headers: getHeaders(),
      });
      const data = await response.json();
      if (data && data.curriculum_graph) {
        setCurriculumGraph(data.curriculum_graph);
        setPhase('graph_ready');
      } else {
        setError('Failed to load curriculum');
        setPhase('error');
      }
    } catch (e) {
      setError(e.message);
      setPhase('error');
    } finally {
      setLoading(false);
    }
  }, [getHeaders, NODE_API, userId]);

  // ── Update graph after node completion ───────────────────────────────────
  const updateGraph = useCallback((newGraph) => {
    setCurriculumGraph(newGraph);
  }, []);

  return {
    phase,
    surveyQuestion,
    surveyProgress,
    curriculumGraph,
    threadId,
    error,
    loading,
    startNewPath,
    submitSurveyAnswer,
    updateGraph,
    loadCurriculum,
  };
}
