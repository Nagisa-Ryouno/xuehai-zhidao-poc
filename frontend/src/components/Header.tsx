import React from 'react';
import { GraduationCap, Sparkles, User, ChevronDown } from 'lucide-react';
import type { StudentListItem } from '../types';

interface HeaderProps {
  students: StudentListItem[];
  currentStudentId: string;
  onSelectStudent: (studentId: string) => void;
  isOnline: boolean;
  isLoading: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  students,
  currentStudentId,
  onSelectStudent,
  isOnline,
  isLoading,
}) => {
  return (
    <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200/80 transition-all">
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

        {/* Right: Service Status & Student Selector */}
        <div className="flex items-center gap-3 sm:gap-4">
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
          <div className="relative flex items-center">
            <div className="relative flex items-center bg-slate-100 hover:bg-slate-200/80 text-slate-800 rounded-xl px-3 py-1.5 border border-slate-200 transition-all cursor-pointer shadow-xs">
              <User className="w-4 h-4 text-indigo-600 mr-2 shrink-0" />
              <select
                aria-label="选择切换当前学习学生"
                value={currentStudentId}
                onChange={(e) => onSelectStudent(e.target.value)}
                disabled={isLoading}
                className="appearance-none bg-transparent pr-7 text-sm font-semibold focus:outline-none cursor-pointer text-slate-800"
              >
                {students.map((stu) => (
                  <option key={stu.student_id} value={stu.student_id}>
                    {stu.student_id} {stu.student_name} ({stu.major} · 正确率 {stu.average_accuracy.toFixed(1)}%)
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2 pointer-events-none" />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
