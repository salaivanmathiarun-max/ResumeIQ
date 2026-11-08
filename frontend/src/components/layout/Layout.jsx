import React, { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { api } from '../../api/client';

export const Layout = ({ children, pageTitle }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState(null);

  // Check health periodically
  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const res = await api.getHealth();
        if (isMounted) setBackendHealthy(res && res.status === 'ok');
      } catch {
        if (isMounted) setBackendHealthy(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50/50 flex">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        backendHealthy={backendHealthy}
      />
      <div className="flex-1 flex flex-col min-w-0 overflow-x-hidden">
        <Header
          onOpenSidebar={() => setSidebarOpen(true)}
          pageTitle={pageTitle}
        />
        <main className="flex-1 p-4 sm:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

