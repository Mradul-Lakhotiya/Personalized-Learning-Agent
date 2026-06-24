/**
 * graphLayout.js — Layout algorithm for the ReactFlow learning graph.
 *
 * Extracted from GraphCanvas.jsx so it can be tested independently
 * and swapped for a dagre/elk layout in the future without touching the UI.
 */

const NODE_W  = 220;
const NODE_H  = 100;
const GAP_X   = 60;
const GAP_Y   = 70;
const SEC_GAP = 120;

/**
 * Converts raw curriculum nodes into ReactFlow-positioned node objects.
 * Groups nodes by section_number and arranges them in a grid per section.
 *
 * @param {Array} rawNodes - Array of LearningNode objects from the curriculum graph.
 * @returns {Array} ReactFlow node objects with position, id, type, and data.
 */
export function layoutNodes(rawNodes) {
  if (!rawNodes || rawNodes.length === 0) return [];

  // Group by section_number
  const sections = {};
  for (const node of rawNodes) {
    const sec = node.section_number || 1;
    if (!sections[sec]) sections[sec] = [];
    sections[sec].push(node);
  }

  const positioned = [];
  let sectionY = 60;
  const sectionKeys = Object.keys(sections).map(Number).sort((a, b) => a - b);

  for (const secNum of sectionKeys) {
    const nodes = sections[secNum];
    const cols  = Math.min(nodes.length, 4);
    const totalW = cols * NODE_W + (cols - 1) * GAP_X;
    const startX = -(totalW / 2) + NODE_W / 2;

    nodes.forEach((node, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      positioned.push({
        id:        node.id,
        type:      'learningNode',
        position:  {
          x: startX + col * (NODE_W + GAP_X),
          y: sectionY + row * (NODE_H + GAP_Y),
        },
        data:      { node },
        draggable: true,
      });
    });

    const rows = Math.ceil(nodes.length / cols);
    sectionY += rows * (NODE_H + GAP_Y) + SEC_GAP;
  }

  return positioned;
}
