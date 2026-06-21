import React, { useMemo } from 'react';
import { ReactFlow, Controls, Background } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export function TopicGraph({ progressData }) {
  const { nodes, edges } = useMemo(() => {
    if (!progressData || progressData.length === 0) return { nodes: [], edges: [] };

    const newNodes = [];
    const newEdges = [];

    // Simple layout logic for horizontal flow
    progressData.forEach((item, index) => {
      const isMastered = item.status === 'mastered';
      const percentage = Math.round(item.mastery_score * 100);
      
      newNodes.push({
        id: item.topic_id || index.toString(),
        position: { x: index * 250 + 50, y: 150 + (index % 2 === 0 ? 0 : 100) },
        data: { 
          label: (
            <div className="flex flex-col items-center justify-center p-2">
              <span className="font-bold text-sm text-slate-800">{item.topics?.name || 'Topic'}</span>
              <span className="text-xs text-slate-600 font-mono mt-1">{percentage}% Mastery</span>
            </div>
          ) 
        },
        style: {
          background: isMastered ? 'rgba(6, 182, 212, 0.9)' : 'rgba(255, 255, 255, 0.9)',
          border: isMastered ? '2px solid #0891b2' : '2px solid #cbd5e1',
          borderRadius: '8px',
          padding: '5px',
          width: 150,
          boxShadow: isMastered ? '0 0 15px rgba(6, 182, 212, 0.5)' : 'none',
        }
      });

      // Connect linearly as a simple default
      if (index > 0) {
        newEdges.push({
          id: `e-${progressData[index-1].topic_id}-${item.topic_id}`,
          source: progressData[index-1].topic_id || (index-1).toString(),
          target: item.topic_id || index.toString(),
          animated: !isMastered,
          style: { stroke: isMastered ? '#06b6d4' : '#64748b', strokeWidth: 2 }
        });
      }
    });

    return { nodes: newNodes, edges: newEdges };
  }, [progressData]);

  if (nodes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500">
        Topic graph will appear here as you learn.
      </div>
    );
  }

  return (
    <div className="h-full w-full rounded-lg overflow-hidden">
      <ReactFlow 
        nodes={nodes} 
        edges={edges}
        fitView
        attributionPosition="bottom-right"
      >
        <Background color="#334155" gap={16} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
