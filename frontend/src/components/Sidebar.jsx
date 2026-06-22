export function Sidebar({ paths, activePath, onPathSelect, onNewPath, onLogout }) {
  // Mock data for previous days if paths are empty, 
  // but we should just render actual paths.
  const historyPaths = paths || [];

  return (
    <nav className="fixed left-0 top-0 h-screen w-sidebar-width bg-surface-container-lowest border-r border-outline-variant flex flex-col py-unit px-4 z-20">
      {/* Header */}
      <div className="mb-6 mt-2 flex flex-col items-start w-full">
        <span className="font-headline-md text-headline-md text-on-surface mb-1">Learning History</span>
        <span className="font-label-md text-label-md text-on-surface-variant">Your recent sessions</span>
      </div>

      {/* CTA */}
      <button 
        onClick={onNewPath}
        className="w-full bg-primary-container text-on-primary py-2 px-4 rounded-lg font-label-md text-label-md hover:opacity-90 transition-opacity mb-6 flex items-center justify-center gap-2 cursor-pointer"
      >
        <span className="material-symbols-outlined text-[18px]">add</span>
        New Session
      </button>

      {/* Navigation Tabs */}
      <div className="flex-1 overflow-y-auto w-full space-y-1">
        <a href="#" className="bg-secondary-container text-on-secondary-container rounded-lg flex items-center gap-3 px-3 py-2 transition-transform duration-200">
          <span className="material-symbols-outlined text-[20px]">account_tree</span>
          <span className="font-label-md text-label-md">Current Path</span>
        </a>
        <a href="#" className="text-on-surface-variant hover:bg-surface-container-low flex items-center gap-3 px-3 py-2 rounded-lg transition-transform duration-200">
          <span className="material-symbols-outlined text-[20px]">auto_stories</span>
          <span className="font-label-md text-label-md">Library</span>
        </a>

        {/* Chat History Entries */}
        <div className="mt-6 mb-2 px-3">
          <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Previous Paths</span>
        </div>
        
        {historyPaths.length === 0 ? (
          <div className="px-3 py-2 text-on-surface-variant font-label-md text-label-md italic">No history yet.</div>
        ) : (
          historyPaths.map((p) => (
            <button
              key={p.thread_id}
              onClick={() => onPathSelect(p)}
              className={`w-full text-left flex items-center gap-3 px-3 py-2 rounded-lg transition-colors group cursor-pointer ${
                activePath === p.thread_id 
                  ? 'bg-surface-container-high text-on-surface' 
                  : 'text-on-surface-variant hover:bg-surface-container-low'
              }`}
            >
              <span className={`material-symbols-outlined text-[16px] transition-colors ${
                activePath === p.thread_id ? 'text-primary' : 'group-hover:text-primary'
              }`}>
                chat_bubble_outline
              </span>
              <span className="font-label-md text-label-md truncate">
                {p.learning_goal || 'Untitled Goal'}
              </span>
            </button>
          ))
        )}
      </div>

      {/* Footer Tabs */}
      <div className="mt-auto pt-4 border-t border-outline-variant space-y-1 w-full pb-4">
        <button onClick={onLogout} className="w-full text-on-surface-variant hover:bg-surface-container-low flex items-center gap-3 px-3 py-2 rounded-lg transition-transform duration-200 cursor-pointer">
          <span className="material-symbols-outlined text-[20px]">logout</span>
          <span className="font-label-md text-label-md">Logout</span>
        </button>
      </div>
    </nav>
  );
}
