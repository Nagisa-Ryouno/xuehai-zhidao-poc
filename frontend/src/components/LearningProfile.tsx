import React from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { UserCheck, Zap, Layers, Sparkles } from 'lucide-react';
import type { OverallProfile } from '../types';

interface LearningProfileProps {
  profile: OverallProfile;
}

export const LearningProfile: React.FC<LearningProfileProps> = ({ profile }) => {
  // Normalize metrics for RadarChart (scale 0 - 100)
  // Activity score: map ~0..350 interactions to 0..100
  const normalizedActivity = Math.min(
    100,
    Math.round((profile.total_interaction_count / 300) * 100)
  );

  // Speed / Efficiency score: ~50s = 95, 120s = 65, 170s = 40
  const normalizedSpeed = Math.max(
    25,
    Math.min(
      100,
      Math.round(110 - profile.average_answer_time_seconds * 0.45)
    )
  );

  const chartData = [
    { subject: '知识掌握', value: Math.round(profile.average_accuracy), fullMark: 100 },
    { subject: '综合评估', value: Math.round(profile.average_assessment_score), fullMark: 100 },
    { subject: '学习完成度', value: Math.round(profile.average_completion_rate), fullMark: 100 },
    { subject: '学习活跃度', value: normalizedActivity, fullMark: 100 },
    { subject: '答题效率', value: normalizedSpeed, fullMark: 100 },
  ];

  return (
    <div className="glass-card rounded-2xl p-6 flex flex-col justify-between h-full">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">我的学习画像</h2>
              <p className="text-xs text-slate-500">五维学情综合雷达分布</p>
            </div>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            {profile.mastery_level}掌握
          </span>
        </div>

        {/* Radar Chart */}
        <div className="w-full h-56 -my-2 flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={chartData}>
              <PolarGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <PolarAngleAxis
                dataKey="subject"
                tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
              />
              <PolarRadiusAxis
                angle={30}
                domain={[0, 100]}
                tick={false}
                axisLine={false}
              />
              <Tooltip
                formatter={(val) => [`${val ?? 0} 分`, '能力值']}
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderRadius: '12px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                  borderColor: '#e2e8f0',
                  fontSize: '12px',
                }}
              />
              <Radar
                name="学情能力"
                dataKey="value"
                stroke="#6366f1"
                fill="#818cf8"
                fillOpacity={0.4}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Behavioral Indicators Grid */}
      <div className="grid grid-cols-3 gap-2.5 pt-4 mt-2 border-t border-slate-100">
        {/* Speed */}
        <div className="bg-slate-50/80 rounded-xl p-2.5 text-center">
          <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
            <Zap className="w-3.5 h-3.5 text-amber-500" />
            <span className="text-[11px] font-medium">答题耗时</span>
          </div>
          <div className="text-xs font-bold text-slate-800 truncate">
            {profile.speed_status}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            均耗 {profile.average_answer_time_seconds.toFixed(0)} 秒/题
          </div>
        </div>

        {/* Activity */}
        <div className="bg-slate-50/80 rounded-xl p-2.5 text-center">
          <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            <span className="text-[11px] font-medium">学习活跃</span>
          </div>
          <div className="text-xs font-bold text-slate-800">
            {profile.activity_level}活跃度
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            {profile.total_interaction_count} 次系统交互
          </div>
        </div>

        {/* Completion */}
        <div className="bg-slate-50/80 rounded-xl p-2.5 text-center">
          <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
            <Layers className="w-3.5 h-3.5 text-emerald-500" />
            <span className="text-[11px] font-medium">任务推进</span>
          </div>
          <div className="text-xs font-bold text-slate-800">
            {profile.completion_level}完成度
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            已达 {profile.average_completion_rate.toFixed(0)}%
          </div>
        </div>
      </div>
    </div>
  );
};
