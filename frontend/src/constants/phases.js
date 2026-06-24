/**
 * phases.js — Single source of truth for UI phase strings.
 *
 * Phases represent the current state of the useLearningPath hook,
 * driving what the UI renders (survey, graph, loading states, etc).
 */

export const PHASE = {
  IDLE:       'idle',
  STARTING:   'starting',
  SURVEY:     'survey',
  GENERATING: 'generating',
  GRAPH_READY:'graph_ready',
  ERROR:      'error',
};
