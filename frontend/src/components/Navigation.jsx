import { NavLink } from 'react-router-dom';
import { BookOpen, LineChart } from 'lucide-react';

export function Navigation() {
  return (
    <nav style={{
      display: 'flex',
      gap: '1rem',
      justifyContent: 'center',
      marginBottom: '2rem',
      padding: '0.5rem',
      background: 'rgba(30, 41, 59, 0.5)',
      borderRadius: '12px',
      border: '1px solid var(--glass-border)'
    }}>
      <NavLink
        to="/learn"
        className={({ isActive }) => `flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${isActive ? 'bg-cyan-900/40 text-cyan-400' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
        style={{ textDecoration: 'none' }}
      >
        <BookOpen size={20} />
        <span className="font-medium">Learn</span>
      </NavLink>
      
      <NavLink
        to="/progress"
        className={({ isActive }) => `flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${isActive ? 'bg-cyan-900/40 text-cyan-400' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
        style={{ textDecoration: 'none' }}
      >
        <LineChart size={20} />
        <span className="font-medium">Progress</span>
      </NavLink>
    </nav>
  );
}
