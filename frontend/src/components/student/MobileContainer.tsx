import React, { type ReactNode } from 'react';
import { BOTTOM_NAV_CONFIG } from './navConfig';

export interface MobileContainerProps {
  children: ReactNode;
  className?: string;
}

export const MobileContainer: React.FC<MobileContainerProps> = ({
  children,
  className = '',
}) => {
  return (
    <div
      className={`w-full max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 ${BOTTOM_NAV_CONFIG.contentPaddingClass} ${className}`}
    >
      {children}
    </div>
  );
};
