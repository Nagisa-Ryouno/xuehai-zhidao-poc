import React from 'react';
import { AlertCircle, RefreshCw, ServerOff } from 'lucide-react';

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
  isRetrying?: boolean;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  message,
  onRetry,
  isRetrying = false,
}) => {
  return (
    <div className="min-h-[50vh] flex items-center justify-center p-6">
      <div className="bg-white rounded-3xl p-8 sm:p-10 border border-slate-200/90 shadow-lg max-w-md w-full text-center space-y-5">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-rose-50 text-rose-500 border border-rose-100 flex items-center justify-center">
          <ServerOff className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <h2 className="text-xl font-bold text-slate-900">
            暂时无法获取学习分析数据
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            {message || '请确认学海智导 AI 后端服务（FastAPI）正在正常运行。'}
          </p>
        </div>

        <div className="bg-slate-50 rounded-xl p-3 text-[11px] text-slate-500 text-left border border-slate-200/60 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
          <span>
            提示：可检查终端执行 <code className="bg-white px-1 py-0.5 rounded border border-slate-200 font-mono text-slate-700">python 04_api.py</code> 是否已就绪。
          </span>
        </div>

        <div>
          <button
            onClick={onRetry}
            disabled={isRetrying}
            className="w-full inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] transition-all shadow-md shadow-indigo-500/20 disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
            {isRetrying ? '正在重连中...' : '重新连接服务'}
          </button>
        </div>
      </div>
    </div>
  );
};
