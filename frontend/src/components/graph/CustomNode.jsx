import { Handle, Position } from '@xyflow/react';
import { NODE_STATUS } from '../../constants/nodeStatus';

const CustomNode = ({ data }) => {
  const node = data.node;
  const status = node.status || NODE_STATUS.LOCKED;

  if (status === NODE_STATUS.COMPLETED) {
    return (
      <div className="w-48 bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-sm cursor-pointer hover:-translate-y-0.5 hover:shadow-md transition-all">
        <Handle type="target" position={Position.Top} className="opacity-0" />
        <div className="flex items-center gap-2 mb-2">
          <div className="w-6 h-6 rounded-full bg-[#D1FAE5] flex items-center justify-center">
            <span className="material-symbols-outlined text-[14px] text-[#065F46]">check</span>
          </div>
          <span className="font-label-sm text-label-sm text-on-surface-variant uppercase">Completed</span>
        </div>
        <h3 className="font-label-md text-label-md text-on-surface font-semibold">{node.title}</h3>
        <Handle type="source" position={Position.Bottom} className="opacity-0" />
      </div>
    );
  }

  if (status === NODE_STATUS.IN_PROGRESS || status === NODE_STATUS.AVAILABLE) {
    return (
      <div className="w-56 bg-[#FFFBEB] border-2 border-dashed border-[#F59E0B] rounded-xl p-4 shadow-md ring-4 ring-[#FEF3C7] ring-opacity-50 cursor-pointer hover:-translate-y-0.5 transition-all">
        <Handle type="target" position={Position.Top} className="opacity-0" />
        <div className="flex items-center gap-2 mb-2">
          <div className="w-6 h-6 rounded-full bg-[#FEF3C7] flex items-center justify-center animate-pulse">
            <span className="material-symbols-outlined text-[14px] text-[#B45309]" style={{ fontVariationSettings: "'FILL' 1" }}>play_arrow</span>
          </div>
          <span className="font-label-sm text-label-sm text-[#B45309] uppercase font-bold">
            {status === NODE_STATUS.IN_PROGRESS ? 'In Progress' : 'Up Next'}
          </span>
        </div>
        <h3 className="font-label-md text-label-md text-on-surface font-bold mb-1">{node.title}</h3>
        {status === NODE_STATUS.IN_PROGRESS && (
          <div className="w-full bg-[#FDE68A] h-1.5 rounded-full overflow-hidden mt-3">
            <div className="bg-[#F59E0B] w-[45%] h-full rounded-full" />
          </div>
        )}
        <Handle type="source" position={Position.Bottom} className="opacity-0" />
      </div>
    );
  }

  // Locked / Upcoming
  return (
    <div className="w-48 bg-[#4F46E5] border border-[#4338CA] rounded-xl p-4 shadow-sm opacity-80 cursor-pointer hover:opacity-100 transition-all">
      <Handle type="target" position={Position.Top} className="opacity-0" />
      <div className="flex items-center gap-2 mb-2">
        <div className="w-6 h-6 rounded-full bg-[#E0E7FF] bg-opacity-20 flex items-center justify-center">
          <span className="material-symbols-outlined text-[14px] text-white">lock</span>
        </div>
        <span className="font-label-sm text-label-sm text-[#E0E7FF] uppercase">Upcoming</span>
      </div>
      <h3 className="font-label-md text-label-md text-white font-semibold">{node.title}</h3>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
    </div>
  );
};

export default CustomNode;
