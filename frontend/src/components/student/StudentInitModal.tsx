import React, { useState } from 'react';
import {
  X,
  Sparkles,
  User,
  Target,
  ArrowRight,
  Check,
} from 'lucide-react';
import type { StudentInitRequest, StudentInitResponse } from '../../api';

interface StudentInitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: StudentInitRequest) => Promise<StudentInitResponse | void>;
  onSelectPresetStudent?: (studentId: string) => void;
}

const PRESET_GOALS = [
  '微观经济学期末冲刺 (冲A)',
  '考研专业课高分夯实',
  '期中考试重点突破',
  '基础概念系统自适应梳理',
];

const PRESET_MAJORS = [
  '经济学',
  '金融学',
  '国际经济与贸易',
  '工商管理',
  '财政学',
];

export const StudentInitModal: React.FC<StudentInitModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  onSelectPresetStudent,
}) => {
  const [studentName, setStudentName] = useState('李华');
  const [major, setMajor] = useState('经济学');
  const [grade, setGrade] = useState('大二');
  const [learningGoal, setLearningGoal] = useState('微观经济学期末冲刺 (冲A)');
  const [startKnowledgeId, setStartKnowledgeId] = useState('K01');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!studentName.trim()) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        student_name: studentName.trim(),
        major,
        grade,
        learning_goal: learningGoal,
        start_knowledge_id: startKnowledgeId,
      });
      onClose();
    } catch (err) {
      console.error('Failed to init student:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickS001 = () => {
    if (onSelectPresetStudent) {
      onSelectPresetStudent('S001');
    }
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="init-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150"
    >
      <div className="glass-card rounded-3xl max-w-lg w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-spring-pop">
        {/* Header */}
        <div className="px-5 sm:px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-indigo-50/80 via-white to-violet-50/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2
                id="init-modal-title"
                className="text-lg font-black text-slate-900 tracking-tight"
              >
                设定学习目标 · 新建学情档案
              </h2>
              <p className="text-xs text-slate-500">
                AI 依据个人认知基线自适应规划最佳通关路径
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭窗口"
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 sm:p-6 overflow-y-auto space-y-4 text-sm text-slate-700">
          {/* Quick Preset Banner */}
          <div className="p-3 rounded-xl bg-indigo-50/70 border border-indigo-100 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-indigo-900 font-medium">
              <User className="w-4 h-4 text-indigo-600 shrink-0" />
              <span>不想填表？直接体验预设标准演示生</span>
            </div>
            <button
              type="button"
              onClick={handleQuickS001}
              className="px-3 py-1.5 rounded-lg bg-white border border-indigo-200 text-indigo-700 text-xs font-bold hover:bg-indigo-50 transition-colors shrink-0 shadow-2xs cursor-pointer"
            >
              载入 S001 (张三)
            </button>
          </div>

          {/* 姓名与专业 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                学生姓名
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  placeholder="例如：李华"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm font-semibold outline-none transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                所学专业
              </label>
              <select
                value={major}
                onChange={(e) => setMajor(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm font-semibold outline-none bg-white transition-all cursor-pointer"
              >
                {PRESET_MAJORS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* 年级与起始考点 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                当前年级
              </label>
              <div className="flex gap-2">
                {['大一', '大二', '大三'].map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setGrade(g)}
                    className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                      grade === g
                        ? 'bg-indigo-600 text-white border-indigo-600 shadow-2xs'
                        : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                首个通关攻坚考点
              </label>
              <select
                value={startKnowledgeId}
                onChange={(e) => setStartKnowledgeId(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm font-semibold outline-none bg-white transition-all cursor-pointer"
              >
                <option value="K01">K01 稀缺性与经济学基本问题</option>
                <option value="K02">K02 机会成本与生产可能性边界</option>
                <option value="K08">K08 需求价格弹性</option>
              </select>
            </div>
          </div>

          {/* 学习目标设定 */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center justify-between">
              <span className="flex items-center gap-1">
                <Target className="w-3.5 h-3.5 text-indigo-600" />
                <span>学习目标设定</span>
              </span>
              <span className="text-[11px] text-slate-400 font-normal">
                AI 将据此加权推荐路径节点
              </span>
            </label>
            <div className="space-y-2">
              {PRESET_GOALS.map((goal) => (
                <div
                  key={goal}
                  onClick={() => setLearningGoal(goal)}
                  className={`p-2.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                    learningGoal === goal
                      ? 'bg-indigo-50/90 border-indigo-300 text-indigo-900 font-bold shadow-2xs'
                      : 'bg-slate-50/60 border-slate-200 hover:bg-slate-100 text-slate-700'
                  }`}
                >
                  <span className="text-xs">{goal}</span>
                  {learningGoal === goal && (
                    <Check className="w-4 h-4 text-indigo-600 shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Footer Submit */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 text-xs sm:text-sm font-semibold transition-all cursor-pointer min-h-[44px]"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !studentName.trim()}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-xs sm:text-sm font-bold shadow-md shadow-indigo-500/20 flex items-center justify-center gap-2 transition-all cursor-pointer min-h-[44px] disabled:opacity-50"
            >
              <span>{isSubmitting ? '正在构建档案...' : '🚀 开启自适应学习旅程'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
