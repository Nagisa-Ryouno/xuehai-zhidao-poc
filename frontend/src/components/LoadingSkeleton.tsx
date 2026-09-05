import React from 'react';

export const LoadingSkeleton: React.FC = () => {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Hero Banner Skeleton */}
      <div className="rounded-2xl bg-white p-8 border border-slate-200/70 h-44 flex flex-col justify-between">
        <div className="space-y-3">
          <div className="flex gap-2">
            <div className="w-24 h-6 bg-slate-200 rounded-full"></div>
            <div className="w-36 h-6 bg-slate-200 rounded-full"></div>
          </div>
          <div className="w-48 h-8 bg-slate-200 rounded-lg"></div>
          <div className="w-96 h-4 bg-slate-200 rounded-md"></div>
        </div>
      </div>

      {/* 6 Stat Cards Skeleton */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-2xl p-5 border border-slate-200/70 h-32 flex flex-col justify-between"
          >
            <div className="flex justify-between items-center">
              <div className="w-16 h-4 bg-slate-200 rounded"></div>
              <div className="w-8 h-8 bg-slate-200 rounded-xl"></div>
            </div>
            <div className="w-20 h-7 bg-slate-200 rounded-lg"></div>
            <div className="w-full h-3 bg-slate-100 rounded"></div>
          </div>
        ))}
      </div>

      {/* Middle 2 Cards Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl p-6 border border-slate-200/70 h-80 space-y-4">
          <div className="w-32 h-6 bg-slate-200 rounded"></div>
          <div className="w-full h-48 bg-slate-100 rounded-xl"></div>
        </div>
        <div className="bg-white rounded-2xl p-6 border border-slate-200/70 h-80 space-y-4">
          <div className="w-32 h-6 bg-slate-200 rounded"></div>
          <div className="w-full h-48 bg-slate-100 rounded-xl"></div>
        </div>
      </div>

      {/* Weak Points Skeleton */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/70 h-64 space-y-4">
        <div className="w-40 h-6 bg-slate-200 rounded"></div>
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-40 bg-slate-100 rounded-xl"></div>
          ))}
        </div>
      </div>

      {/* Learning Path Skeleton */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/70 h-72 space-y-4">
        <div className="w-48 h-6 bg-slate-200 rounded"></div>
        <div className="space-y-3">
          <div className="h-16 bg-slate-100 rounded-xl"></div>
          <div className="h-16 bg-slate-100 rounded-xl"></div>
        </div>
      </div>
    </div>
  );
};
