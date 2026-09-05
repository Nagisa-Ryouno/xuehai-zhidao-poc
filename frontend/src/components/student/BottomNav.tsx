import React from 'react';
import { CalendarCheck, Network, UserCheck, Bot } from 'lucide-react';
import { useApp } from '../../context/useApp';
import { STUDENT_NAV_TABS, BOTTOM_NAV_CONFIG } from './navConfig';

const ICON_MAP = {
  CalendarCheck,
  Network,
  UserCheck,
  Bot,
} as const;

export const BottomNav: React.FC = () => {
  const { subRoute, navigate } = useApp();

  return (
    <nav
      aria-label="学生端底部主导航"
      className={BOTTOM_NAV_CONFIG.containerClass}
    >
      <div className="max-w-md mx-auto flex items-center justify-around px-2 py-1">
        {STUDENT_NAV_TABS.map((tab) => {
          const Icon = ICON_MAP[tab.iconName as keyof typeof ICON_MAP] || CalendarCheck;
          const isActive = subRoute === tab.id;

          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => navigate(tab.path)}
              aria-current={isActive ? 'page' : undefined}
              className={`flex-1 min-h-[48px] min-w-[48px] py-1 px-1 flex flex-col items-center justify-center rounded-2xl transition-all duration-200 cursor-pointer ${
                isActive
                  ? 'text-indigo-600 font-bold'
                  : 'text-slate-500 hover:text-slate-900 active:scale-95'
              }`}
            >
              <div
                className={`relative flex items-center justify-center p-1 rounded-xl transition-colors ${
                  isActive ? 'bg-indigo-50' : ''
                }`}
              >
                <Icon className={`w-5 h-5 transition-transform ${isActive ? 'scale-110' : ''}`} />
                {isActive && (
                  <span className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-indigo-600 rounded-full" />
                )}
              </div>
              <span className="text-[11px] leading-tight tracking-tight mt-0.5 whitespace-nowrap">
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
