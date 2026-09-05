import React from 'react';
import { GraduationCap } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-12 py-8 border-t border-slate-200/80 bg-white/50 text-slate-500 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 font-medium text-slate-700">
          <GraduationCap className="w-4 h-4 text-indigo-600" />
          <span>学海智导 (Xuehai Zhidao)</span>
          <span className="text-slate-300">|</span>
          <span className="text-slate-500">AI驱动的大学生个性化学习成长助手</span>
        </div>
        <div className="text-slate-400 text-center sm:text-right">
          国家级大学生创新创业训练计划项目 · 阶段五：前端可视化 Demo
        </div>
      </div>
    </footer>
  );
};
