import React from 'react';

export function CurriculumTimeline({ progressData }) {
  if (!progressData || progressData.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500">
        No timeline data available yet.
      </div>
    );
  }

  return (
    <div className="h-64 overflow-y-auto pr-2 custom-scrollbar">
      <div className="flex flex-col gap-4">
        {progressData.map((item, index) => {
          const percentage = Math.round(item.mastery_score * 100);
          const isMastered = item.status === 'mastered';
          
          return (
            <div key={item.topic_id || index} className="flex flex-col gap-2">
              <div className="flex justify-between items-center text-sm">
                <span className={`font-medium ${isMastered ? 'text-cyan-400' : 'text-slate-300'}`}>
                  {item.topics?.name || 'Unknown Topic'}
                </span>
                <span className="text-slate-400 font-mono text-xs">
                  {percentage}%
                </span>
              </div>
              
              <div className="w-full bg-slate-800 rounded-full h-2.5 border border-slate-700 overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all duration-1000 ease-out ${isMastered ? 'bg-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.5)]' : 'bg-indigo-500'}`}
                  style={{ width: `${percentage}%` }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
