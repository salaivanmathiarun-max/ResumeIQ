import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner = ({ label = 'Loading...', size = 'md', className = '' }) => {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-10 h-10',
  };

  return (
    <div className={`flex flex-col items-center justify-center py-8 ${className}`}>
      <Loader2 className={`${sizes[size] || sizes.md} animate-spin text-indigo-600 mb-2`} />
      {label && <p className="text-sm font-medium text-slate-500">{label}</p>}
    </div>
  );
};

