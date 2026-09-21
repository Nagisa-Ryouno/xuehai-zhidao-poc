import React from 'react';
import { GraduationCap, LayoutDashboard } from 'lucide-react';
import { useApp } from '../context/useApp';
import type { AppRole } from '../router';

export const RoleSwitcher: React.FC = () => {
  const { role, switchRole, studentId } = useApp();

  const handleSwitch = (targetRole: AppRole) => {
    if (role !== targetRole) {
      switchRole(targetRole);
    }
  };

  return (
    <div className="flex items-center gap-1.5 p-1 bg-slate-100/90 rounded-xl border border-slate-200/80 shadow-xs">
      <button
        type="button"
        onClick={() => handleSwitch('student')}
        className={`flex items-center justify-center gap-1.5 px-2.5 sm:px-3 py-1.5 min-w-[38px] min-h-[38px] sm:min-w-0 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer ${
          role === 'student'
            ? 'bg-white text-indigo-700 shadow-sm shadow-slate-200/60 font-bold border border-slate-200/60'
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
        }`}
        title={`切换到学生视图 (当前学情: ${studentId})`}
      >
        <GraduationCap className={`w-3.5 h-3.5 ${role === 'student' ? 'text-indigo-600' : 'text-slate-400'}`} />
        <span className="hidden sm:inline">学生视图</span>
      </button>

      <button
        type="button"
        onClick={() => handleSwitch('teacher')}
        className={`flex items-center justify-center gap-1.5 px-2.5 sm:px-3 py-1.5 min-w-[38px] min-h-[38px] sm:min-w-0 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer ${
          role === 'teacher'
            ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30 font-bold'
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
        }`}
        title={`切换到教师学情决策驾驶舱 (关联学生: ${studentId})`}
      >
        <LayoutDashboard className={`w-3.5 h-3.5 ${role === 'teacher' ? 'text-indigo-200' : 'text-slate-400'}`} />
        <span className="hidden sm:inline">教师驾驶舱</span>
      </button>
    </div>
  );
};
