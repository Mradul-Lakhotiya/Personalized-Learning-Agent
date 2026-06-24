import { useState, useCallback, useRef } from 'react';
import { startSession, submitSurveyAnswer as apiSubmitAnswer, generateCurriculum as apiGenerateCurriculum } from '../services/aiApi';
import { fetchCurriculum } from '../services/pathApi';
import { PHASE } from '../constants/phases';

export function useLearningPath(sessionToken, userId) {
  const [phase, setPhase]                   = useState(PHASE.IDLE);
  const [surveyQuestion, setSurveyQuestion] = useState(null);
  const [surveyProgress, setSurveyProgress] = useState(null);
  const [curriculumGraph, setCurriculumGraph] = useState(null);
  const [error, setError]                   = useState(null);
  const [loading, setLoading]               = useState(false);
  const [threadId, setThreadId]             = useState(null);
  const threadIdRef = useRef(null);

  // ── SSE stream reader helper ──────────────────────────────────────────────
  const readSSEStream = async (response, onPayload) => {
    const reader  = response.body.getReader();
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
          } catch { /* ignore parse errors */ }
        }
      }
    } finally {
      reader.releaseLock();
    }
  };

  // ── Start a new session ───────────────────────────────────────────────────
  const startNewPath = useCallback(async (learningGoal) => {
    setLoading(true);
    setError(null);
    setPhase(PHASE.STARTING);

    const newThreadId = `thread-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    threadIdRef.current = newThreadId;
    setThreadId(newThreadId);

    try {
      const response = await startSession(newThreadId, learningGoal, sessionToken);
      await readSSEStream(response, (data) => {
        if (data.type === 'execution_complete') {
          const p = data.payload;
          if (p?.phase === 'onboarding' && p?.survey_question) {
            setSurveyQuestion(p.survey_question);
            setSurveyProgress(p.survey_progress);
            setPhase(PHASE.SURVEY);
          } else if (p?.phase === 'graph_ready' && p?.curriculum_graph) {
            setCurriculumGraph(p.curriculum_graph);
            setPhase(PHASE.GRAPH_READY);
          }
        } else if (data.type === 'fatal_error') {
          setError(data.message);
          setPhase(PHASE.ERROR);
        }
      });
    } catch (e) {
      setError(e.message);
      setPhase(PHASE.ERROR);
    } finally {
      setLoading(false);
    }
  }, [sessionToken]);

  // ── Generate curriculum after survey ─────────────────────────────────────
  const generateCurriculum = useCallback(async () => {
    if (!threadIdRef.current) return;
    setLoading(true);
    setError(null);

    try {
      const response = await apiGenerateCurriculum(threadIdRef.current, sessionToken);
      await readSSEStream(response, (data) => {
        if (data.type === 'execution_complete') {
          const p = data.payload;
          if (p?.phase === 'graph_ready' && p?.curriculum_graph) {
            setCurriculumGraph(p.curriculum_graph);
            setPhase(PHASE.GRAPH_READY);
          }
        } else if (data.type === 'fatal_error') {
          setError(data.message);
          setPhase(PHASE.ERROR);
        }
      });
    } catch (e) {
      setError(e.message);
      setPhase(PHASE.ERROR);
    } finally {
      setLoading(false);
    }
  }, [sessionToken]);

  // ── Submit one survey answer ──────────────────────────────────────────────
  const submitSurveyAnswer = useCallback(async (topic, rating) => {
    if (!threadIdRef.current) return;
    setLoading(true);
    setError(null);

    try {
      const data = await apiSubmitAnswer(threadIdRef.current, topic, rating, sessionToken);

      if (data.survey_complete) {
        setPhase(PHASE.GENERATING);
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
  }, [sessionToken, generateCurriculum]);

  // ── Load curriculum for existing session ─────────────────────────────────
  const loadCurriculum = useCallback(async (existingThreadId) => {
    setLoading(true);
    setError(null);
    threadIdRef.current = existingThreadId;
    setThreadId(existingThreadId);

    try {
      if (!userId) throw new Error('User ID is required to load curriculum');
      const data = await fetchCurriculum(userId, existingThreadId, sessionToken);
      if (data?.curriculum_graph) {
        setCurriculumGraph(data.curriculum_graph);
        setPhase(PHASE.GRAPH_READY);
      } else {
        setError('Failed to load curriculum');
        setPhase(PHASE.ERROR);
      }
    } catch (e) {
      setError(e.message);
      setPhase(PHASE.ERROR);
    } finally {
      setLoading(false);
    }
  }, [userId]);

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
