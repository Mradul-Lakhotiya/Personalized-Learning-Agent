import { useMemo } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';

export function SkillMap({ progressData }) {
  const chartData = useMemo(() => {
    if (!progressData || progressData.length === 0) return [];
    
    // We map progress data to format: { subject: 'Topic Name', A: 100 }
    return progressData.map(item => ({
      subject: item.topics?.name || 'Unknown Topic',
      A: Math.round(item.mastery_score * 100), // convert 0-1 to 0-100
      fullMark: 100
    }));
  }, [progressData]);

  if (chartData.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500">
        Start learning to build your skill map!
      </div>
    );
  }

  // To make it look good, radar chart works best with at least 3 points.
  // If we only have 1 or 2 topics, we can pad it with empty ones.
  const paddedData = [...chartData];
  while (paddedData.length < 3) {
    paddedData.push({ subject: `Topic ${paddedData.length + 1}`, A: 0, fullMark: 100 });
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={paddedData}>
          <PolarGrid stroke="rgba(255,255,255,0.1)" />
          <PolarAngleAxis 
            dataKey="subject" 
            tick={{ fill: '#94a3b8', fontSize: 12 }} 
          />
          <PolarRadiusAxis 
            angle={30} 
            domain={[0, 100]} 
            tick={{ fill: '#475569', fontSize: 10 }}
            tickCount={5}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
            itemStyle={{ color: '#22d3ee' }}
          />
          <Radar 
            name="Mastery" 
            dataKey="A" 
            stroke="#06b6d4" 
            fill="#06b6d4" 
            fillOpacity={0.5} 
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
