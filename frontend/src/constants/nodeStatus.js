/**
 * nodeStatus.js — Single source of truth for node status strings.
 *
 * Import this everywhere instead of using magic strings like 'locked'.
 * If a status ever changes, update it here and nowhere else.
 */

export const NODE_STATUS = {
  LOCKED:      'locked',
  AVAILABLE:   'available',
  IN_PROGRESS: 'in_progress',
  COMPLETED:   'completed',
};

/** @returns {boolean} */
export const isUnlocked = (status) =>
  status === NODE_STATUS.AVAILABLE || status === NODE_STATUS.IN_PROGRESS || status === NODE_STATUS.COMPLETED;
