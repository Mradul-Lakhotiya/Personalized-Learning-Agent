import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import { useAuth } from '../context/AuthContext';
import { SkillMap } from '../components/SkillMap';
import { CurriculumTimeline } from '../components/CurriculumTimeline';
import { TopicGraph } from '../components/TopicGraph';

export function ProgressDashboard() {
  const { user } = useAuth();
  const [progressData, setProgressData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    
    const fetchProgress = async () => {
      const { data, error } = await supabase
        .from('user_progress')
        .select(`
          topic_id,
          mastery_score,
          status,
          topics ( name )
        `)
        .eq('user_id', user.id);
        
      if (!error && data) {
        setProgressData(data);
      }
      setLoading(false);
    };
    
    fetchProgress();
  }, [user]);

  if (loading) {
    return <div className="text-center text-slate-400 mt-10">Loading progress...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <h2 className="text-2xl font-bold gradient-text mb-4">Your Learning Journey</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-panel p-6 rounded-xl">
          <h3 className="text-lg font-semibold mb-4 text-slate-200">Skill Map</h3>
          <SkillMap progressData={progressData} />
        </div>
        
        <div className="glass-panel p-6 rounded-xl">
          <h3 className="text-lg font-semibold mb-4 text-slate-200">Curriculum Timeline</h3>
          <CurriculumTimeline progressData={progressData} />
        </div>
      </div>
      
      <div className="glass-panel p-6 rounded-xl mt-4">
        <h3 className="text-lg font-semibold mb-4 text-slate-200">Knowledge Graph</h3>
        <div className="h-96 w-full text-slate-500 border border-slate-700/50 rounded-lg overflow-hidden">
          <TopicGraph progressData={progressData} />
        </div>
      </div>
    </div>
  );
}
