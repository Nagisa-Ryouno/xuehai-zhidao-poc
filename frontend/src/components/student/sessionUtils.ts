/**
 * sessionUtils.ts
 * 学习会话辅助纯函数与人本化文本处理
 */

/**
 * 人本化呈现推荐理由，将偶现的内部编码 K\d+ 防御性转换为自然考点名称 (UX-ISSUE-06)
 */
export function sanitizeRecommendationReason(rawReason?: string, kpName?: string): string {
  if (!rawReason) return '根据你当前的学习进展，为你挑选了该辅导材料。';
  const bracketedName = kpName ? `「${kpName}」` : '「当前考点」';
  const plainName = kpName || '当前考点';

  return rawReason
    .replace(/考点\s*K\d+\s*/gi, bracketedName)
    .replace(/K\d+/gi, plainName);
}

/**
 * 依据作答表现解析结果页的推荐 CTA 行为模式 (UX-ISSUE-02)
 * <60% 优先推荐再练一次（主按钮），仍允许继续下一步（次按钮）
 * >=60% 优先推荐继续下一步（主按钮），允许再练一次（次按钮）
 */
export interface ResultCtaConfig {
  primaryLabel: string;
  primaryAction: 'RETRY' | 'NEXT';
  secondaryLabel: string;
  secondaryAction: 'RETRY' | 'NEXT';
  isPassing: boolean;
}

export function getResultCtaConfig(accuracyPercent: number): ResultCtaConfig {
  if (accuracyPercent < 60) {
    return {
      primaryLabel: '再练一次 (推荐巩固)',
      primaryAction: 'RETRY',
      secondaryLabel: '仍继续下一步',
      secondaryAction: 'NEXT',
      isPassing: false,
    };
  }
  return {
    primaryLabel: '继续下一步',
    primaryAction: 'NEXT',
    secondaryLabel: '再练一次',
    secondaryAction: 'RETRY',
    isPassing: true,
  };
}
