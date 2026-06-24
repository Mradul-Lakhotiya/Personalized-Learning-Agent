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
import { layoutNodes } from '../../utils/graphLayout';

const NODE_TYPES = { learningNode: CustomNode };

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

  React.useEffect(() => { setNodes(flowNodes); }, [flowNodes, setNodes]);
  React.useEffect(() => { setEdges(flowEdges); }, [flowEdges, setEdges]);

  const handleNodeClick = useCallback((_event, node) => {
    if (node.data?.node?.status !== 'locked') {
      onNodeClick?.(node.data.node);
    }
  }, [onNodeClick]);

  if (rawNodes.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 text-slate-400">
        <div className="text-5xl">🗺️</div>
        <p className="text-base">Your learning path will appear here.</p>
        <p className="text-sm opacity-60">
          Click <strong className="text-cyan-400">+ New Path</strong> in the sidebar to get started.
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
