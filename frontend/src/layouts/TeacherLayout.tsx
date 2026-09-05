import React from 'react';
import {
  Users,
  Send,
  Sparkles,
  TrendingUp,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { useApp } from '../context/useApp';
import type { StudentListItem } from '../types';

interface TeacherLayoutProps {
  students: StudentListItem[];
  isOnline: boolean;
  isLoading: boolean;
  onSelectStudent: (studentId: string) => void;
}

export const TeacherLayout: React.FC<TeacherLayoutProps> = ({
  students,
  isOnline,
  isLoading,
  onSelectStudent,
}) => {
  const { studentId, switchRole } = useApp();
  const currentStudent = students.find((s) => s.student_id === studentId);

  return (
    <div className="min-h-screen flex flex-col bg-slate-100/80 text-slate-900 selection:bg-indigo-100 selection:text-indigo-800">
      {/* Teacher Cockpit Top Header */}
      <Header
        students={students}
        currentStudentId={studentId}
        onSelectStudent={onSelectStudent}
        isOnline={isOnline}
        isLoading={isLoading}
      />

      {/* Main Cockpit Content (Wide Desktop Layout) */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Cockpit Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-slate-900/10 border border-slate-800 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 text-xs font-semibold">
                <Sparkles className="w-3.5 h-3.5" />
                教师学情决策驾驶舱 · 宽屏看板 (Teacher Cockpit)
              </div>
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
                班级学情监控与闭环干预中心
              </h1>
              <p className="text-sm text-slate-300 max-w-2xl">
                宏观掌握班级掌握度分布、实时识别认知卡点高危学生，一键生成针对性干预指引。
              </p>
            </div>

            {/* Current Monitored Student Context Pill */}
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/15 flex items-center gap-4 shrink-0">
              <div className="w-12 h-12 rounded-xl bg-indigo-500 flex items-center justify-center text-white font-bold text-lg shadow-md">
                {studentId}
              </div>
              <div>
                <div className="text-xs text-slate-300 font-medium">当前下钻学生上下文</div>
                <div className="text-base font-bold text-white">
                  {currentStudent?.student_name || studentId} ({currentStudent?.major || '经济学'})
                </div>
                <div className="text-xs text-indigo-300 mt-0.5">
                  正确率: {currentStudent ? `${currentStudent.average_accuracy.toFixed(1)}%` : '--'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 3 Major Teacher Modules Preview Grid (Placeholders for P0-10 ~ P0-12) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Module 1: Class Overview (P0-10) */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4 hover:border-indigo-200 transition-colors">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
                <Users className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200/60">
                P0-10 预留
              </span>
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">班级全景学情看板</h3>
              <p className="text-xs text-slate-500 mt-1">
                聚合 S001~S005 宏观认知达标率、章节平均掌握度及班级共性薄弱知识点排行。
              </p>
            </div>
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400 font-medium">
              <span>在 P0-10 阶段实现</span>
              <ChevronRight className="w-4 h-4" />
            </div>
          </div>

          {/* Module 2: Multidimensional Risk Radar (P0-11) */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4 hover:border-amber-200 transition-colors">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/60">
                P0-11 预留
              </span>
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">多维风险预警雷达</h3>
              <p className="text-xs text-slate-500 mt-1">
                解耦正确率与 BKT 潜在掌握度，综合做题耗时与导论前置断层评定 CRITICAL / WARNING 风险等级。
              </p>
            </div>
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400 font-medium">
              <span>在 P0-11 阶段实现</span>
              <ChevronRight className="w-4 h-4" />
            </div>
          </div>

          {/* Module 3: Targeted Intervention Cockpit (P0-12) */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4 hover:border-emerald-200 transition-colors">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                <Send className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                P0-12 预留
              </span>
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">针对性干预工作台</h3>
              <p className="text-xs text-slate-500 mt-1">
                调阅单个学生历史事件流（做题、求助、耗时），支持一键生成 AI 辅助个性化教学面谈与干预建议。
              </p>
            </div>
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400 font-medium">
              <span>在 P0-12 阶段实现</span>
              <ChevronRight className="w-4 h-4" />
            </div>
          </div>
        </div>

        {/* Quick Switcher Callout */}
        <div className="bg-indigo-50/60 border border-indigo-100 rounded-2xl p-5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-indigo-950">当前处于教师驾驶舱 (Teacher View)</h4>
              <p className="text-xs text-indigo-700">
                若需体验学生端移动优先 4-Tab 学习任务与知识图谱，可随时通过顶栏切换。
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => switchRole('student')}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-sm shrink-0 cursor-pointer"
          >
            返回学生视图
          </button>
        </div>
      </main>

      <Footer />
    </div>
  );
};
