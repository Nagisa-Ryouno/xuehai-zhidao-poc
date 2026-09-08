import React from 'react';
import { Network, UserCheck, Bot, ArrowRight } from 'lucide-react';

interface TasksQuickNavProps {
  onNavigate: (path: string) => void;
}

export const TasksQuickNav: React.FC<TasksQuickNavProps> = ({ onNavigate }) => {
  const quickLinks = [
    {
      title: '知识图谱全景',
      desc: '探索完整微观经济学知识依赖网络与前置拓扑',
      path: '/student/graph',
      icon: Network,
      color: 'text-indigo-600 bg-indigo-50 border-indigo-200',
      actionLabel: '查看知识图谱 →',
    },
    {
      title: '学情档案与弱项',
      desc: '查看多维能力雷达、薄弱考点清单与历史做题分析',
      path: '/student/profile',
      icon: UserCheck,
      color: 'text-emerald-600 bg-emerald-50 border-emerald-200',
      actionLabel: '查看完整学情 →',
    },
    {
      title: 'AI 学习伴学导师',
      desc: '针对当前疑惑考点进行苏格拉底式答疑与引导',
      path: '/student/assistant',
      icon: Bot,
      color: 'text-violet-600 bg-violet-50 border-violet-200',
      actionLabel: '询问 AI 导师 →',
    },
  ];

  return (
    <div className="space-y-3 pt-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-900">拓展学习与辅助工具</h3>
        <span className="text-xs text-slate-400">各功能模块专区</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {quickLinks.map((item) => {
          const Icon = item.icon;
          return (
            <button
              type="button"
              key={item.path}
              onClick={() => onNavigate(item.path)}
              className="group p-4 bg-white hover:bg-slate-50/80 rounded-xl border border-slate-200/90 shadow-2xs hover:shadow-xs transition-all cursor-pointer flex flex-col justify-between min-h-[100px] text-left w-full"
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg border ${item.color} shrink-0`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <h4 className="text-xs sm:text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                    {item.title}
                  </h4>
                  <p className="text-[11px] sm:text-xs text-slate-500 mt-0.5 line-clamp-2 leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-end gap-1 text-xs font-semibold text-indigo-600 group-hover:translate-x-0.5 transition-transform">
                <span>{item.actionLabel.replace(' →', '')}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
