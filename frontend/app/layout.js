'use client';
import { useState, useEffect } from 'react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import './globals.css';

export default function RootLayout({ children }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Initialize sidebar collapsed state from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('sidebar_collapsed');
      if (stored === 'true') {
        setSidebarCollapsed(true);
      }
    } catch {
      // ignore
    }
  }, []);

  // Persist sidebar collapsed state to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('sidebar_collapsed', String(sidebarCollapsed));
    } catch {
      // ignore
    }
  }, [sidebarCollapsed]);

  return (
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Content Studio — AI LinkedIn Content Creation</title>
      </head>
      <body className="antialiased bg-gray-50 min-h-screen">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          mobileOpen={mobileMenuOpen}
          onMobileClose={() => setMobileMenuOpen(false)}
        />
        <div
          className={`${
            sidebarCollapsed ? 'md:ml-16' : 'md:ml-60'
          } transition-all duration-200 min-h-screen flex flex-col`}
        >
          <Header onMobileMenuToggle={() => setMobileMenuOpen(true)} />
          <main className="flex-1 overflow-auto p-4 lg:p-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
