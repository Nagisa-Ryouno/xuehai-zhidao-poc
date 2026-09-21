import React from 'react';
import { GraduationCap, Sparkles, User, ChevronDown, Plus } from 'lucide-react';
import type { StudentListItem } from '../types';
import { RoleSwitcher } from './RoleSwitcher';

interface HeaderProps {
  students: StudentListItem[];
  currentStudentId: string;
  onSelectStudent: (studentId: string) => void;
  isOnline: boolean;
  isLoading: boolean;
  onOpenInitModal?: () => void;
  onOpenPretestModal?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  students,
  currentStudentId,
  onSelectStudent,
  isOnline,
  isLoading,
  onOpenInitModal,
  onOpenPretestModal,
}) => {
  return (
    <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200/80 transition-all pt-[env(safe-area-inset-top)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
        {/* Left: Brand & Identity */}
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <GraduationCap className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-slate-900">
                学海智导
              </span>
              <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                <Sparkles className="w-3 h-3 text-indigo-500" />
                AI Learning Pilot
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden md:block">
              AI驱动的个性化学习成长助手
            </p>
          </div>
        </div>

        {/* Right: Service Status, Role Switcher & Student Selector */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Dual-Role Switcher (Student View <-> Teacher Cockpit) */}
          <RoleSwitcher />

          {/* Backend Health Pill */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
              isOnline
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80'
                : 'bg-rose-50 text-rose-700 border-rose-200/80'
            }`}
            title={isOnline ? 'FastAPI 后端连接畅通' : 'FastAPI 后端未连接'}
          >
            <span className="relative flex h-2 w-2">
              {isOnline && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              )}
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  isOnline ? 'bg-emerald-500' : 'bg-rose-500'
                }`}
              ></span>
            </span>
            <span className="hidden sm:inline">
              {isOnline ? 'AI分析服务在线' : '分析服务离线'}
            </span>
          </div>

          {/* Student Selector Dropdown */}
          <div className="relative flex items-center gap-1.5 sm:gap-2">
            <div className="relative flex items-center bg-slate-100 hover:bg-slate-200/80 text-slate-800 rounded-xl px-2.5 sm:px-3 py-1.5 min-h-[40px] border border-slate-200 transition-all cursor-pointer shadow-xs max-w-[140px] sm:max-w-none">
              <User className="w-4 h-4 text-indigo-600 mr-1.5 sm:mr-2 shrink-0" />
              <select
                aria-label="选择切换当前学习学生"
                id="student-select"
                value={currentStudentId}
                onChange={(e) => onSelectStudent(e.target.value)}
                disabled={isLoading}
                className="appearance-none bg-transparent pr-6 sm:pr-7 py-1 text-xs sm:text-sm font-semibold focus:outline-none cursor-pointer text-slate-800 truncate"
              >
                {students.map((stu) => (
                  <option key={stu.student_id} value={stu.student_id}>
                    {stu.student_id} {stu.student_name} ({stu.major} · 正确率 {stu.average_accuracy.toFixed(1)}%)
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2 pointer-events-none" />
            </div>

            {onOpenPretestModal && (
              <button
                type="button"
                onClick={onOpenPretestModal}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-bold border border-purple-200/80 transition-all cursor-pointer shadow-2xs shrink-0"
                title="启动 3 题极速前测与学情诊断"
              >
                <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                <span className="hidden sm:inline">3题前测摸底</span>
              </button>
            )}

            {onOpenInitModal && (
              <button
                type="button"
                onClick={onOpenInitModal}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold border border-indigo-200/80 transition-all cursor-pointer shadow-2xs shrink-0"
                title="设定个性化学习目标或新建演示学生"
              >
                <Plus className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">设定目标 / 新学生</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
