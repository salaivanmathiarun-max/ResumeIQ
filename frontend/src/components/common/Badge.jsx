import React from 'react';

export const Badge = ({ children, variant = 'default', size = 'sm', className = '' }) => {
  const variants = {
    default: 'bg-slate-100 text-slate-700 border-slate-200',
    primary: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    warning: 'bg-amber-50 text-amber-700 border-amber-200',
    danger: 'bg-rose-50 text-rose-700 border-rose-200',
    pdf: 'bg-rose-50 text-rose-700 border-rose-200',
    docx: 'bg-blue-50 text-blue-700 border-blue-200',
  };

  const sizes = {
    xs: 'px-1.5 py-0.5 text-[10px]',
    sm: 'px-2.5 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${variants[variant] || variants.default} ${sizes[size]} ${className}`}
    >
      {children}
    </span>
  );
};

export const StatusBadge = ({ status }) => {
  const norm = (status || '').toLowerCase();
  if (norm === 'completed') {
    return <Badge variant="success">Completed</Badge>;
  }
  if (norm === 'pending') {
    return <Badge variant="warning">Pending</Badge>;
  }
  if (norm === 'failed') {
    return <Badge variant="danger">Failed</Badge>;
  }
  return <Badge variant="default">{status || 'Unknown'}</Badge>;
};

