/**
 * aiApi.js — All calls to the Python AI backend (port 8000).
 *
 * This is the single place to update if the Python backend URL or route
 * structure changes. The useLearningPath hook imports from here.
 */

const BASE = `${import.meta.env.VITE_AI_API_BASE_URL || 'http://localhost:8000'}/api/v1`;

const jsonHeaders = (token) => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${token}`,
});

/**
 * Start a new learning session (or resume an existing one).
 * @returns {Promise<Response>} Raw SSE stream response.
 */
export async function startSession(threadId, learningGoal, sessionToken) {
  return fetch(`${BASE}/agent/start`, {
    method: 'POST',
    headers: jsonHeaders(sessionToken),
    body: JSON.stringify({ thread_id: threadId, initial_prompt: learningGoal }),
  });
}

/**
 * Submit one self-assessment survey answer.
 * @returns {Promise<{survey_complete, next_question?, progress?, skill_ratings?}>}
 */
export async function submitSurveyAnswer(threadId, topic, rating, sessionToken) {
  const res = await fetch(`${BASE}/agent/survey-answer`, {
    method: 'POST',
    headers: jsonHeaders(sessionToken),
    body: JSON.stringify({ thread_id: threadId, topic, rating }),
  });
  if (!res.ok) throw new Error(`submitSurveyAnswer failed: ${res.status}`);
  return res.json();
}

/**
 * Trigger curriculum generation after all survey answers are in.
 * @returns {Promise<Response>} Raw SSE stream response.
 */
export async function generateCurriculum(threadId, sessionToken) {
  return fetch(`${BASE}/agent/generate-curriculum`, {
    method: 'POST',
    headers: jsonHeaders(sessionToken),
    body: JSON.stringify({ thread_id: threadId }),
  });
}

/**
 * End a session (triggers background memory consolidation on the server).
 * @returns {Promise<{status, message}>}
 */
export async function endSession(threadId, sessionToken) {
  const res = await fetch(`${BASE}/agent/end`, {
    method: 'POST',
    headers: jsonHeaders(sessionToken),
    body: JSON.stringify({ thread_id: threadId }),
  });
  if (!res.ok) throw new Error(`endSession failed: ${res.status}`);
  return res.json();
}
