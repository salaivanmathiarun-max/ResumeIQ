import React from 'react';
import { Menu, User, UploadCloud } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useCandidate } from '../../context/CandidateContext';
import { Button } from '../common/Button';

export const Header = ({ onOpenSidebar, pageTitle }) => {
  const { activeCandidate } = useCandidate();

  return (
    <header className="h-16 bg-white border-b border-slate-200/90 px-4 sm:px-8 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenSidebar}
          className="md:hidden text-slate-500 hover:text-slate-800 p-1.5 rounded-lg border border-slate-200"
          aria-label="Open sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
            {pageTitle || 'ResumeIQ Platform'}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {activeCandidate ? (
          <Link
            to="/profile"
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50/70 hover:bg-slate-100 transition-colors text-xs text-slate-700"
          >
            <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-[11px]">
              {activeCandidate.full_name?.charAt(0).toUpperCase() || 'U'}
            </div>
            <span className="font-medium hidden sm:inline max-w-[140px] truncate">
              {activeCandidate.full_name}
            </span>
          </Link>
        ) : (
          <Link to="/profile">
            <Button variant="secondary" size="sm" icon={User}>
              Set Profile
            </Button>
          </Link>
        )}

        <Link to="/upload" className="hidden sm:inline-block">
          <Button variant="primary" size="sm" icon={UploadCloud}>
            Upload Resume
          </Button>
        </Link>
      </div>
    </header>
  );
};

