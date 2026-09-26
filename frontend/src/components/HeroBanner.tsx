import React from 'react';
import { Target, Compass, BookOpen } from 'lucide-react';
import type { StudentBasic } from '../types';
import { getStudentDisplayName } from '../utils/student';

interface HeroBannerProps {
  student: StudentBasic;
  recommendationType: string;
}

export const HeroBanner: React.FC<HeroBannerProps> = ({
  student,
  recommendationType,
}) => {
  // Strategy tag color mapping
  const getStrategyStyle = (type: string) => {
    switch (type) {
      case '综合能力提升':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200/80';
      case '基础补强':
        return 'bg-amber-50 text-amber-700 border-amber-200/80';
      case '高参与度转化训练':
        return 'bg-blue-50 text-blue-700 border-blue-200/80';
      case '薄弱知识点强化':
      default:
        return 'bg-indigo-50 text-indigo-700 border-indigo-200/80';
    }
  };

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-white via-indigo-50/30 to-violet-50/20 border border-slate-200/80 p-6 sm:p-8 shadow-xs">
      {/* Subtle decorative background blur */}
      <div className="absolute -right-16 -top-16 w-64 h-64 bg-indigo-200/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute right-32 -bottom-16 w-64 h-64 bg-violet-200/20 rounded-full blur-3xl pointer-events-none" />

      <div className="relative flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        {/* Left: Greeting & Identity */}
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
              <BookOpen className="w-3.5 h-3.5 text-slate-500" />
              {student.major} · {student.grade}
            </span>
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${getStrategyStyle(
                recommendationType
              )}`}
            >
              <Compass className="w-3.5 h-3.5" />
              当前策略：{recommendationType || '个性化学习推荐'}
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            你好，{getStudentDisplayName(student.student_id, student.student_name)} <span className="inline-block animate-wave">👋</span>
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-2xl leading-relaxed">
            今天也来看看自己的学习进展吧。系统已结合你的多维答题行为与微观知识图谱，动态更新了个性化诊断。
          </p>
        </div>

        {/* Right: Learning Goal Card */}
        <div className="lg:max-w-md w-full bg-white/90 backdrop-blur-xs rounded-xl p-4 sm:p-5 border border-slate-200/80 shadow-xs">
          <div className="flex items-center gap-2 mb-2 text-indigo-700 font-semibold text-xs tracking-wider uppercase">
            <Target className="w-4 h-4 text-indigo-600 shrink-0" />
            <span>个人学习目标</span>
          </div>
          <p className="text-xs sm:text-sm text-slate-700 leading-relaxed font-medium">
            "{student.learning_goal}"
          </p>
        </div>
      </div>
    </div>
  );
};
