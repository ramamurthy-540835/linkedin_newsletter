'use client';
import { useState, useEffect, useCallback } from 'react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import DraftCartFlyout from '@/components/DraftCartFlyout';
import DraftCartContext from '@/lib/DraftCartContext';
import './globals.css';

const CART_KEY = 'content_studio_draft_cart';

export default function RootLayout({ children }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [cart, setCart] = useState([]);
  const [toast, setToast] = useState('');

  useEffect(() => {
    try {
      const stored = localStorage.getItem('sidebar_collapsed');
      if (stored === 'true') setSidebarCollapsed(true);
    } catch {}
    try {
      const stored = localStorage.getItem(CART_KEY);
      if (stored) setCart(JSON.parse(stored));
    } catch {}
  }, []);

  useEffect(() => {
    try { localStorage.setItem('sidebar_collapsed', String(sidebarCollapsed)); } catch {}
  }, [sidebarCollapsed]);

  const addToCart = useCallback((item) => {
    const entry = {
      id: Date.now() + '-' + Math.random().toString(36).slice(2, 7),
      createdAt: Date.now(),
      status: 'draft',
      ...item,
    };
    setCart(prev => {
      const updated = [entry, ...prev];
      try { localStorage.setItem(CART_KEY, JSON.stringify(updated)); } catch {}
      return updated;
    });
  }, []);

  const removeFromCart = useCallback((id) => {
    setCart(prev => {
      const updated = prev.filter(i => i.id !== id);
      try { localStorage.setItem(CART_KEY, JSON.stringify(updated)); } catch {}
      return updated;
    });
  }, []);

  return (
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Content Studio — AI LinkedIn Content Creation</title>
      </head>
      <body className="antialiased bg-gray-50 min-h-screen">
        <DraftCartContext.Provider value={{ cart, addToCart, removeFromCart }}>
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
            <Header
              onMobileMenuToggle={() => setMobileMenuOpen(true)}
              cartCount={cart.length}
              onCartToggle={() => setCartOpen(true)}
            />
            <main className="flex-1 overflow-auto p-4 lg:p-6">{children}</main>
          </div>
          <DraftCartFlyout
            open={cartOpen}
            onClose={() => setCartOpen(false)}
            items={cart}
            onRemove={removeFromCart}
            onToast={setToast}
          />
        </DraftCartContext.Provider>
        {toast && <ToastMsg message={toast} onDone={() => setToast('')} />}
      </body>
    </html>
  );
}

function ToastMsg({ message, onDone }) {
  useEffect(() => { const t = setTimeout(onDone, 3000); return () => clearTimeout(t); }, [onDone]);
  return (
    <div className="fixed bottom-4 right-4 z-[60] bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-xl shadow-elevated text-sm font-medium animate-slide-up max-w-sm">
      {message}
    </div>
  );
}
