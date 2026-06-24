/**
 * pathApi.js — All calls to the Go State/CRUD backend (port 4000).
 *
 * This is the single place to update if the Go backend URL or route
 * structure changes. Components and hooks import from here.
 */

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4000';

/** Build the base URL for a specific user's conversations. */
const convBase = (userId) => `${BASE}/api/v1/users/${userId}/conversations`;

/**
 * Fetch all learning paths for a user.
 * @returns {Promise<{paths: Array}>}
 */
export async function fetchConversations(userId, sessionToken) {
  const res = await fetch(convBase(userId), {
    headers: { Authorization: `Bearer ${sessionToken}` }
  });
  if (!res.ok) throw new Error(`fetchConversations failed: ${res.status}`);
  return res.json();
}

/**
 * Fetch a single curriculum graph by thread ID.
 * @returns {Promise<{phase, curriculum_graph, completed_node_ids, learning_goal}>}
 */
export async function fetchCurriculum(userId, threadId, sessionToken) {
  const res = await fetch(`${convBase(userId)}/${threadId}`, {
    headers: { Authorization: `Bearer ${sessionToken}` }
  });
  if (!res.ok) throw new Error(`fetchCurriculum failed: ${res.status}`);
  return res.json();
}

/**
 * Fetch cached node details (resources, questions).
 * @returns {Promise<object>} The path_nodes row.
 */
export async function fetchNodeDetails(userId, threadId, nodeId, sessionToken) {
  const res = await fetch(`${convBase(userId)}/${threadId}/nodes/${nodeId}`, {
    headers: { Authorization: `Bearer ${sessionToken}` }
  });
  if (!res.ok) throw new Error(`fetchNodeDetails failed: ${res.status}`);
  return res.json();
}

/**
 * Stream resource generation for a node via SSE.
 * @returns {Promise<Response>} Raw fetch Response — caller reads the SSE stream.
 */
export async function streamNodeGeneration(userId, threadId, nodeId, sessionToken) {
  return fetch(`${convBase(userId)}/${threadId}/nodes/${nodeId}/generate`, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  });
}

/**
 * Mark a node as completed. Returns the updated curriculum graph.
 * @returns {Promise<{success, completed_node_id, curriculum_graph}>}
 */
export async function completeNode(userId, threadId, nodeId, sessionToken) {
  const res = await fetch(`${convBase(userId)}/${threadId}/nodes/${nodeId}/complete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${sessionToken}`,
    },
  });
  if (!res.ok) throw new Error(`completeNode failed: ${res.status}`);
  return res.json();
}
