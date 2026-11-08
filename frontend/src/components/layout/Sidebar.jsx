import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  FileText,
  User,
  Sparkles,
  Activity,
  X,
} from 'lucide-react';
import { useCandidate } from '../../context/CandidateContext';

export const Sidebar = ({ isOpen, onClose, backendHealthy }) => {
  const { activeCandidate } = useCandidate();

  const navItems = [
    { name: 'Dashboard', to: '/', icon: LayoutDashboard },
    { name: 'Upload Resume', to: '/upload', icon: UploadCloud },
    { name: 'Resume History', to: '/history', icon: FileText },
    { name: 'Candidate Profile', to: '/profile', icon: User },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-xs md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-white border-r border-slate-200/90 flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-slate-100">
          <NavLink to="/" className="flex items-center gap-2.5" onClick={onClose}>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-sm shadow-indigo-200">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-slate-900 flex items-center gap-1">
                Resume<span className="text-indigo-600">IQ</span>
              </span>
              <span className="block text-[10px] font-medium text-slate-400 tracking-wider uppercase">
                Career Intelligence
              </span>
            </div>
          </NavLink>
          <button
            onClick={onClose}
            className="md:hidden text-slate-400 hover:text-slate-600 p-1 rounded-md"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3.5 py-5 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`
                }
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Active Candidate Widget */}
        <div className="p-3.5 mx-3 mb-3 rounded-xl bg-slate-50 border border-slate-200/80">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
            <span>Active Candidate</span>
            <NavLink
              to="/profile"
              onClick={onClose}
              className="text-indigo-600 hover:text-indigo-700 font-medium normal-case text-xs"
            >
              {activeCandidate ? 'Switch' : 'Set Profile'}
            </NavLink>
          </div>
          {activeCandidate ? (
            <div>
              <p className="text-sm font-semibold text-slate-900 truncate">
                {activeCandidate.full_name}
              </p>
              <p className="text-xs text-slate-500 truncate">{activeCandidate.email}</p>
              <div className="mt-2 inline-block">
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-indigo-100/70 text-indigo-700 capitalize">
                  {activeCandidate.candidate_type}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500">
              No candidate selected.{' '}
              <NavLink to="/profile" onClick={onClose} className="text-indigo-600 underline">
                Select or create
              </NavLink>
            </p>
          )}
        </div>

        {/* System Health Status Footer */}
        <div className="px-6 py-3.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <span className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                backendHealthy === true
                  ? 'bg-emerald-500'
                  : backendHealthy === false
                  ? 'bg-rose-500'
                  : 'bg-amber-400 animate-pulse'
              }`}
            />
            <span>
              Backend:{' '}
              <strong className="text-slate-700 font-medium">
                {backendHealthy === true ? 'Online' : backendHealthy === false ? 'Offline' : 'Checking'}
              </strong>
            </span>
          </span>
          <Activity className="w-3.5 h-3.5 text-slate-400" />
        </div>
      </aside>
    </>
  );
};

