import React from 'react';
import {
  CheckCircle2,
  Award,
  TrendingUp,
  Activity,
  Clock,
  FileCheck,
} from 'lucide-react';
import type { OverallProfile } from '../types';

interface StatCardsProps {
  profile: OverallProfile;
}

export const StatCards: React.FC<StatCardsProps> = ({ profile }) => {
  // Convert minutes to "X小时Y分钟"
  const formatMinutes = (totalMinutes: number) => {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = Math.round(totalMinutes % 60);
    if (hours === 0) return `${minutes}分钟`;
    return `${hours}小时${minutes}分钟`;
  };

  // Helper for mastery level badge color
  const getMasteryBadgeClass = (level: string) => {
    switch (level) {
      case '较好':
      case '高':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case '中等':
      case '中':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case '偏弱':
      case '较弱':
      case '低':
      default:
        return 'bg-amber-50 text-amber-700 border-amber-200';
    }
  };

  const cards = [
    {
      title: '平均正确率',
      value: `${profile.average_accuracy.toFixed(1)}%`,
      badge: profile.mastery_level,
      badgeClass: getMasteryBadgeClass(profile.mastery_level),
      icon: CheckCircle2,
      iconColor: 'text-indigo-600 bg-indigo-50',
      description: `掌握程度：${profile.mastery_level}`,
    },
    {
      title: '综合评估得分',
      value: `${profile.average_assessment_score.toFixed(1)}`,
      badge: '综合表现',
      badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
      icon: Award,
      iconColor: 'text-blue-600 bg-blue-50',
      description: '基于多维测验加权评定',
    },
    {
      title: '学习完成度',
      value: `${profile.average_completion_rate.toFixed(1)}%`,
      badge: `${profile.completion_level}完成率`,
      badgeClass: getMasteryBadgeClass(profile.completion_level),
      icon: TrendingUp,
      iconColor: 'text-emerald-600 bg-emerald-50',
      description: '章节任务节点推进率',
    },
    {
      title: '学习活跃度',
      value: `${profile.total_interaction_count}`,
      unit: '次互动',
      badge: `${profile.activity_level}活跃`,
      badgeClass: getMasteryBadgeClass(profile.activity_level),
      icon: Activity,
      iconColor: 'text-violet-600 bg-violet-50',
      description: '系统内交互与问答频次',
    },
    {
      title: '累计学习时长',
      value: formatMinutes(profile.total_learning_time_minutes),
      badge: '有效投入',
      badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
      icon: Clock,
      iconColor: 'text-amber-600 bg-amber-50',
      description: `折合 ${profile.total_learning_time_minutes} 分钟`,
    },
    {
      title: '累计练习题数',
      value: `${profile.total_practice_count}`,
      unit: '道题',
      badge: '题目覆盖',
      badgeClass: 'bg-cyan-50 text-cyan-700 border-cyan-200',
      icon: FileCheck,
      iconColor: 'text-cyan-600 bg-cyan-50',
      description: '微观经济学各章习题',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-slate-500">
                  {card.title}
                </span>
                <div className={`p-2 rounded-xl ${card.iconColor}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>

              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-2xl font-black text-slate-900 tracking-tight">
                  {card.value}
                </span>
                {card.unit && (
                  <span className="text-xs font-semibold text-slate-500">
                    {card.unit}
                  </span>
                )}
              </div>
            </div>

            <div className="pt-3 mt-1 border-t border-slate-100 flex items-center justify-between">
              <span className="text-[11px] text-slate-400 truncate max-w-[120px]">
                {card.description}
              </span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${card.badgeClass}`}
              >
                {card.badge}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
