import { Network, Bot, ArrowRight, AlertCircle, Award } from 'lucide-react';

interface TasksQuickNavProps {
  onNavigate: (path: string) => void;
  wrongCount?: number;
  onSelectProfileTab?: (tab: 'progress' | 'wrong_answers' | 'radar') => void;
}

export const TasksQuickNav: React.FC<TasksQuickNavProps> = ({
  onNavigate,
  wrongCount = 0,
  onSelectProfileTab,
}) => {
  const quickLinks = [
    {
      title: '知识图谱全景',
      desc: '探索 30 考点认知依赖网络与动态航线高亮',
      icon: Network,
      color: 'text-indigo-600 bg-indigo-50 border-indigo-200',
      actionLabel: '查看知识图谱',
      onClick: () => onNavigate('/student/graph'),
    },
    {
      title: '30考点掌握度全览',
      desc: '基于认知追踪模型查看全图谱考点掌握矩阵与真实演化',
      icon: Award,
      color: 'text-emerald-600 bg-emerald-50 border-emerald-200',
      actionLabel: '查看掌握度',
      onClick: () => {
        if (onSelectProfileTab) onSelectProfileTab('progress');
        onNavigate('/student/profile');
      },
    },
    {
      title: '错题复盘本',
      desc: wrongCount > 0 ? `当前有 ${wrongCount} 道待复盘错题，可一键再学再练` : '当前无待复盘错题，继续保持',
      icon: AlertCircle,
      color: 'text-rose-600 bg-rose-50 border-rose-200',
      actionLabel: wrongCount > 0 ? `复盘错题 (${wrongCount})` : '查看错题本',
      badge: wrongCount > 0 ? `${wrongCount} 道待复盘` : undefined,
      onClick: () => {
        if (onSelectProfileTab) onSelectProfileTab('wrong_answers');
        onNavigate('/student/profile');
      },
    },
    {
      title: 'AI 学习伴学导师',
      desc: '针对当前疑惑考点进行苏格拉底式答疑与引导',
      icon: Bot,
      color: 'text-violet-600 bg-violet-50 border-violet-200',
      actionLabel: '询问 AI 导师',
      onClick: () => onNavigate('/student/assistant'),
    },
  ];

  return (
    <div className="space-y-3 pt-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-900">拓展学习与成效专区</h3>
        <span className="text-xs text-slate-400">学情深度沉淀</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {quickLinks.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              type="button"
              key={idx}
              onClick={item.onClick}
              className="group p-4 bg-white hover:bg-slate-50/80 rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-xs transition-all cursor-pointer flex flex-col justify-between min-h-[110px] text-left w-full"
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-xl border ${item.color} shrink-0`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-1">
                    <h4 className="text-xs sm:text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                      {item.title}
                    </h4>
                    {item.badge && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 shrink-0">
                        {item.badge}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] sm:text-xs text-slate-500 mt-0.5 line-clamp-2 leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-end gap-1 text-xs font-semibold text-indigo-600 group-hover:translate-x-0.5 transition-transform">
                <span>{item.actionLabel}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
