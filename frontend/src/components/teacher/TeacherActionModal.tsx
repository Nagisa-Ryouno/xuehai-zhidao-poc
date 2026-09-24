import React, { useState } from 'react';
import { X, BookOpen, HelpCircle, BookmarkCheck, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import type { TeacherActionType, TeacherActionItem } from '../../types';
import { postTeacherAction } from '../../api';
import { useBodyScrollLock } from '../../utils/useBodyScrollLock';

export interface TeacherActionModalProps {
  isOpen: boolean;
  studentId: string;
  studentName: string;
  knowledgeId: string;
  knowledgeName: string;
  onClose: () => void;
  onSuccess?: (createdAction: TeacherActionItem) => void;
}

interface ActionOptionConfig {
  type: TeacherActionType;
  title: string;
  badge: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  badgeColor: string;
}

const ACTION_OPTIONS: ActionOptionConfig[] = [
  {
    type: 'REVIEW_CONCEPT',
    title: '建议复习该考点',
    badge: '复习建议',
    description: '向学生推荐该考点的概念速览微卡，引导重温核心概念与易错陷阱。',
    icon: BookOpen,
    badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  },
  {
    type: 'RETRY_PRACTICE',
    title: '建议重新练习',
    badge: '练习建议',
    description: '向学生推荐该考点的微测验，鼓励通过精准刷题查漏补缺。',
    icon: HelpCircle,
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  {
    type: 'MARK_FOLLOWED',
    title: '标记为已关注',
    badge: '仅教师可见',
    description: '在教师端记录关注状态，用于学情跟进与教学反思（不打扰学生）。',
    icon: BookmarkCheck,
    badgeColor: 'bg-slate-100 text-slate-700 border-slate-200',
  },
];

export const TeacherActionModal: React.FC<TeacherActionModalProps> = ({
  isOpen,
  studentId,
  studentName,
  knowledgeId,
  knowledgeName,
  onClose,
  onSuccess,
}) => {
  useBodyScrollLock(isOpen);

  const [selectedAction, setSelectedAction] = useState<TeacherActionType>('REVIEW_CONCEPT');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const currentOption = ACTION_OPTIONS.find((opt) => opt.type === selectedAction)!;

  const handleSubmit = async () => {
    if (isSubmitting) return;

    setIsSubmitting(true);
    setError(null);

    try {
      // 严格仅发送 knowledge_id 与 action_type，绝不生成 action_id / teacher_id / created_at
      const createdAction = await postTeacherAction(studentId, {
        knowledge_id: knowledgeId,
        action_type: selectedAction,
      });

      const successFeedback =
        selectedAction === 'MARK_FOLLOWED'
          ? '已成功记录教师关注'
          : '已成功记录教学建议';
      setToastMessage(successFeedback);

      // 稍作停留展示 Toast 确认后回调关闭
      setTimeout(() => {
        onSuccess?.(createdAction);
        onClose();
      }, 600);
    } catch (err) {
      setError(err instanceof Error ? err.message : '记录教学动作失败，请稍后重试');
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-slate-950/50 backdrop-blur-xs animate-in fade-in duration-150"
      data-testid="teacher-action-modal"
    >
      <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-indigo-400" />
            <h3 className="text-sm font-bold text-white tracking-wide">
              发起教学动作 · 任课教师
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-50 cursor-pointer"
            aria-label="关闭对话框"
            data-testid="btn-close-action-modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {/* Target Student & Knowledge Context */}
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs flex items-center justify-between">
            <div>
              <span className="text-slate-500 font-medium">目标学生：</span>
              <span className="font-bold text-slate-900 ml-1">{studentName}</span>
              <span className="font-mono text-slate-500 ml-1 text-[11px]">({studentId})</span>
            </div>
            <div className="text-right">
              <span className="text-slate-500 font-medium">目标考点：</span>
              <span className="font-mono font-bold text-indigo-700 ml-1">{knowledgeId}</span>
              <span className="font-medium text-slate-800 ml-1">{knowledgeName}</span>
            </div>
          </div>

          {/* Action Selector (3 options strictly) */}
          <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-700">选择教学动作：</div>
            <div className="space-y-2">
              {ACTION_OPTIONS.map((opt) => {
                const IconComponent = opt.icon;
                const isSelected = selectedAction === opt.type;
                return (
                  <button
                    key={opt.type}
                    type="button"
                    onClick={() => {
                      if (!isSubmitting) setSelectedAction(opt.type);
                    }}
                    disabled={isSubmitting}
                    className={`w-full p-3 rounded-xl border text-left transition-all cursor-pointer flex items-start gap-3 ${
                      isSelected
                        ? 'border-indigo-600 bg-indigo-50/40 shadow-xs'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'
                    } ${isSubmitting ? 'opacity-60 cursor-not-allowed' : ''}`}
                    data-testid={`action-option-${opt.type}`}
                  >
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                        isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      <IconComponent className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900">{opt.title}</span>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${opt.badgeColor}`}
                        >
                          {opt.badge}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">
                        {opt.description}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Secondary Confirmation Prompt */}
          <div className="p-3 rounded-xl bg-amber-50/60 border border-amber-200/80 text-[11px] text-amber-900 leading-relaxed">
            <div className="font-semibold flex items-center gap-1.5 text-amber-800">
              <CheckCircle2 className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <span>动作确认与说明</span>
            </div>
            <p className="mt-1 text-slate-700">
              确认向 <span className="font-bold text-slate-900">{studentName}</span> 针对考点{' '}
              <span className="font-bold text-slate-900">
                【{knowledgeId} {knowledgeName}】
              </span>{' '}
              记录<span className="font-bold text-indigo-700">「{currentOption.title}」</span>吗？
            </p>
            <p className="mt-1 text-slate-500 text-[10px]">
              说明：教学动作仅作为教师关注流水与学生端辅助引导，绝对不直接修改学生掌握度概率与知识图谱节点状态。
            </p>
          </div>

          {/* Success Toast / Feedback */}
          {toastMessage && (
            <div
              className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2 animate-in fade-in"
              data-testid="teacher-action-toast"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{toastMessage}</span>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div
              className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center gap-2 animate-in fade-in"
              data-testid="teacher-action-error"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-end gap-2.5 shrink-0">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-200/60 transition-colors disabled:opacity-50 cursor-pointer"
            data-testid="btn-cancel-action"
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || !!toastMessage}
            className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-xs flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
            data-testid="btn-confirm-action"
          >
            {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            <span>{isSubmitting ? '记录中...' : '确认记录'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
