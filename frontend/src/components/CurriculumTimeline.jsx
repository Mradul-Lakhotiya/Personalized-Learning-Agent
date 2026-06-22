export function CurriculumTimeline({ progressData = [], curriculaData = [] }) {
  if (!curriculaData || curriculaData.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500">
        No timeline data available yet.
      </div>
    );
  }

  return (
    <div className="h-64 overflow-y-auto pr-2 custom-scrollbar">
      <div className="flex flex-col gap-4">
        {curriculaData.map((item, index) => {
          const progressItem = progressData.find(p => p.topics?.name === item.topic);
          const percentage = progressItem ? Math.round(progressItem.mastery_score * 100) : 0;
          const isMastered = item.status === 'completed' || (progressItem && progressItem.status === 'mastered');
          const isActive = item.status === 'active';
          
          let titleColor = 'text-slate-500'; // pending
          if (isMastered) titleColor = 'text-cyan-400';
          else if (isActive) titleColor = 'text-purple-400 font-bold';
          
          return (
            <div key={item.id || index} className="flex flex-col gap-2">
              <div className="flex justify-between items-center text-sm">
                <span className={`font-medium ${titleColor}`}>
                  {item.topic || 'Unknown Topic'} {item.status === 'pending' && '🔒'}
                </span>
                <span className={`font-mono text-xs ${isMastered ? 'text-cyan-400' : 'text-slate-400'}`}>
                  {item.status === 'pending' ? 'Locked' : `${percentage}%`}
                </span>
              </div>
              
              <div className="w-full bg-slate-800 rounded-full h-2.5 border border-slate-700 overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all duration-1000 ease-out ${isMastered ? 'bg-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.5)]' : 'bg-purple-500'}`}
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
