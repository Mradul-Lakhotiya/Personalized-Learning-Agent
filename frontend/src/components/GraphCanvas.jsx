import React, { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import CustomNode from './CustomNode';

const NODE_TYPES = { learningNode: CustomNode };

// ── Layout: arrange nodes in a top-to-bottom sectioned grid ──────────────────
function layoutNodes(rawNodes) {
  if (!rawNodes || rawNodes.length === 0) return [];

  // Group by section_number
  const sections = {};
  for (const node of rawNodes) {
    const sec = node.section_number || 1;
    if (!sections[sec]) sections[sec] = [];
    sections[sec].push(node);
  }

  const NODE_W = 220;
  const NODE_H = 100;
  const GAP_X  = 60;
  const GAP_Y  = 70;
  const SEC_GAP = 120;

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
        id:       node.id,
        type:     'learningNode',
        position: {
          x: startX + col * (NODE_W + GAP_X),
          y: sectionY + row * (NODE_H + GAP_Y),
        },
        data: { node },
        draggable: true,
      });
    });

    const rows = Math.ceil(nodes.length / cols);
    sectionY += rows * (NODE_H + GAP_Y) + SEC_GAP;
  }

  return positioned;
}

export function GraphCanvas({ curriculumGraph, onNodeClick }) {
  const rawNodes = useMemo(() => curriculumGraph?.nodes || [], [curriculumGraph]);
  const rawEdges = useMemo(() => curriculumGraph?.edges || [], [curriculumGraph]);

  const flowNodes = useMemo(() => layoutNodes(rawNodes), [rawNodes]);

  const flowEdges = useMemo(() =>
    rawEdges.map(e => ({
      ...e,
      type: 'smoothstep',
      animated: e.animated,
      className: e.animated ? 'graph-line-animated' : 'graph-line',
      style: {
        stroke: e.animated ? '#2563EB' : '#CBD5E1',
        strokeWidth: 2,
      },
      markerEnd: {
        type: 'arrowclosed',
        color: e.animated ? '#2563EB' : '#CBD5E1',
      },
    })),
  [rawEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  React.useEffect(() => {
    setNodes(flowNodes);
  }, [flowNodes, setNodes]);

  React.useEffect(() => {
    setEdges(flowEdges);
  }, [flowEdges, setEdges]);

  const handleNodeClick = useCallback((_event, node) => {
    if (node.data?.node?.status !== 'locked') {
      onNodeClick?.(node.data.node);
    }
  }, [onNodeClick]);

  if (rawNodes.length === 0) {
    return (
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: '1rem', color: '#475569'
      }}>
        <div style={{ fontSize: '3rem' }}>🗺️</div>
        <p style={{ fontSize: '1rem' }}>Your learning path will appear here.</p>
        <p style={{ fontSize: '0.85rem', opacity: 0.6 }}>
          Click <strong style={{ color: '#06b6d4' }}>+ New Path</strong> in the sidebar to get started.
        </p>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        attributionPosition="bottom-right"
        minZoom={0.3}
        maxZoom={2}
      >
        <Background variant={BackgroundVariant.Dots} color="#1e293b" gap={20} size={1} />
        <Controls style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(255,255,255,0.08)' }} />
        <MiniMap
          nodeColor={(node) => {
            const s = node.data?.node?.status;
            if (s === 'completed')   return '#10b981';
            if (s === 'available')   return '#06b6d4';
            if (s === 'in_progress') return '#8b5cf6';
            return '#1e293b';
          }}
          style={{ background: 'rgba(11,15,25,0.8)', border: '1px solid rgba(255,255,255,0.08)' }}
          maskColor="rgba(0,0,0,0.5)"
        />
      </ReactFlow>
    </div>
  );
}
