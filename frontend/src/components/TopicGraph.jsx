import { useMemo } from 'react';
import { ReactFlow, Controls, Background } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export function TopicGraph({ progressData = [], curriculaData = [] }) {
  const { nodes, edges } = useMemo(() => {
    if (!curriculaData || curriculaData.length === 0) return { nodes: [], edges: [] };

    const newNodes = [];
    const newEdges = [];

    // Map the curriculum linear path
    curriculaData.forEach((item, index) => {
      // Check if there is progress for this topic name
      const progressItem = progressData.find(p => p.topics?.name === item.topic);
      const isMastered = item.status === 'completed' || (progressItem && progressItem.status === 'mastered');
      const isActive = item.status === 'active';
      const isPending = item.status === 'pending';
      
      const percentage = progressItem ? Math.round(progressItem.mastery_score * 100) : 0;
      
      let background = 'rgba(15, 23, 42, 0.9)'; // default dark
      let border = '2px solid #334155';
      let shadow = 'none';
      let textColor = 'text-slate-400';
      
      if (isMastered) {
        background = 'rgba(6, 182, 212, 0.9)'; // Cyan
        border = '2px solid #0891b2';
        shadow = '0 0 15px rgba(6, 182, 212, 0.5)';
        textColor = 'text-white';
      } else if (isActive) {
        background = 'rgba(139, 92, 246, 0.9)'; // Purple
        border = '2px solid #a855f7';
        shadow = '0 0 20px rgba(168, 85, 247, 0.6)';
        textColor = 'text-white';
      }
      
      newNodes.push({
        id: item.id || index.toString(),
        position: { x: index * 250 + 50, y: 150 + (index % 2 === 0 ? 0 : 100) },
        data: { 
          label: (
            <div className="flex flex-col items-center justify-center p-2">
              <span className={`font-bold text-sm ${textColor}`}>{item.topic || 'Topic'}</span>
              <span className={`text-xs font-mono mt-1 ${isMastered || isActive ? 'text-white/80' : 'text-slate-500'}`}>
                {isPending ? 'Locked 🔒' : `${percentage}% Mastery`}
              </span>
            </div>
          ) 
        },
        style: {
          background,
          border,
          borderRadius: '8px',
          padding: '5px',
          width: 150,
          boxShadow: shadow,
        }
      });

      // Connect linearly
      if (index > 0) {
        newEdges.push({
          id: `e-${curriculaData[index-1].id}-${item.id}`,
          source: curriculaData[index-1].id || (index-1).toString(),
          target: item.id || index.toString(),
          animated: isActive || isPending,
          style: { 
            stroke: isMastered ? '#06b6d4' : (isActive ? '#a855f7' : '#334155'), 
            strokeWidth: 2 
          }
        });
      }
    });

    return { nodes: newNodes, edges: newEdges };
  }, [progressData, curriculaData]);

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
