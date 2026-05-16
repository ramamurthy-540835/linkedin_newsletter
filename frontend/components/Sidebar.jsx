'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  IconDashboard,
  IconCreate,
  IconLibrary,
  IconQueue,
  IconCompass,
  IconTrending,
  IconBarChart,
  IconSettings,
  IconLinkedIn,
  IconChevronLeft,
  IconChevronRight,
  IconX,
  IconLogOut,
  IconSparkles,
} from '@/components/icons';

const MENU_ITEMS = [
  { href: '/', label: 'Dashboard', icon: IconDashboard },
  { href: '/create', label: 'Create', icon: IconCreate, accent: true },
  { href: '/library', label: 'Content Library', icon: IconLibrary },
  { href: '/publish', label: 'Publish Queue', icon: IconQueue },
  { href: '/discovery', label: 'Discovery', icon: IconCompass },
  { href: '/trends', label: 'Trends', icon: IconTrending },
  { href: '/analytics', label: 'Analytics', icon: IconBarChart },
  { href: '/admin/settings', label: 'Settings', icon: IconSettings },
];

function ConnectionStatus() {
  const [connected, setConnected] = useState(false);
  const [name, setName] = useState('');

  useEffect(() => {
    try {
      const raw = localStorage.getItem('linkedin_oauth');
      if (raw) {
        const data = JSON.parse(raw);
        setConnected(!!data.access_token);
        setName(data.name || '');
      }
    } catch {
      // ignore
    }
  }, []);

  return (
    <div className="flex items-center gap-2 px-2 py-2 mb-1">
      <div
        className={`w-2 h-2 rounded-full flex-shrink-0 ${
          connected ? 'bg-green-500' : 'bg-amber-400'
        }`}
      />
      <span className="text-xs text-gray-500 truncate">
        {connected ? name || 'LinkedIn Connected' : 'Not Connected'}
      </span>
    </div>
  );
}

function NavItem({ item, active, collapsed }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={`flex items-center gap-3 px-3 py-2 rounded-xl text-sm transition-all duration-150 ${
        active
          ? 'bg-gradient-to-r from-studio-50 to-linkedin-50 text-studio-700 font-semibold shadow-sm border border-studio-100'
          : item.accent
          ? 'text-gray-600 hover:bg-studio-50 hover:text-studio-700'
          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
      } ${collapsed ? 'justify-center' : ''}`}
      title={collapsed ? item.label : undefined}
    >
      <Icon size={20} className={`flex-shrink-0 ${active ? 'text-studio-600' : ''}`} />
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );
}

export default function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }) {
  const pathname = usePathname();
  const router = useRouter();

  const isActive = (href) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  const handleLogout = () => {
    localStorage.removeItem('linkedin_oauth');
    router.push('/');
    window.location.reload();
  };

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={`hidden md:flex flex-col ${
          collapsed ? 'w-16' : 'w-60'
        } transition-all duration-200 bg-white border-r border-gray-200 h-screen fixed left-0 top-0 z-30`}
      >
        {/* Logo section */}
        <div className="p-4 border-b border-gray-100 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-studio-600 to-linkedin-600 flex items-center justify-center flex-shrink-0">
            <IconSparkles size={18} className="text-white" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-bold text-gray-900 text-sm leading-tight">Content Studio</span>
              <span className="text-[10px] text-gray-400 leading-tight">AI-Powered</span>
            </div>
          )}
        </div>

        {/* Navigation items */}
        <nav className="flex-1 py-3 px-2 space-y-0.5">
          {MENU_ITEMS.map((item) => (
            <NavItem
              key={item.href}
              item={item}
              active={isActive(item.href)}
              collapsed={collapsed}
            />
          ))}
        </nav>

        {/* Bottom section */}
        <div className="border-t border-gray-100 p-3">
          {!collapsed && <ConnectionStatus />}

          <button
            onClick={handleLogout}
            className={`flex items-center gap-3 w-full px-3 py-2 rounded-xl text-sm text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors ${
              collapsed ? 'justify-center' : ''
            }`}
            title={collapsed ? 'Logout' : undefined}
          >
            <IconLogOut size={18} className="flex-shrink-0" />
            {!collapsed && <span>Logout</span>}
          </button>

          <button
            onClick={onToggle}
            className={`flex items-center gap-3 w-full px-3 py-2 rounded-xl text-sm text-gray-400 hover:bg-gray-50 hover:text-gray-600 transition-colors mt-1 ${
              collapsed ? 'justify-center' : ''
            }`}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <IconChevronRight size={18} />
            ) : (
              <>
                <IconChevronLeft size={18} className="flex-shrink-0" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={onMobileClose}
          />
          <aside className="relative w-72 h-full bg-white animate-slide-in flex flex-col">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-studio-600 to-linkedin-600 flex items-center justify-center">
                  <IconSparkles size={18} className="text-white" />
                </div>
                <div className="flex flex-col">
                  <span className="font-bold text-gray-900 text-sm leading-tight">Content Studio</span>
                  <span className="text-[10px] text-gray-400 leading-tight">AI-Powered</span>
                </div>
              </div>
              <button
                onClick={onMobileClose}
                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <IconX size={20} className="text-gray-500" />
              </button>
            </div>

            <nav className="flex-1 py-3 px-2 space-y-0.5">
              {MENU_ITEMS.map((item) => (
                <NavItem
                  key={item.href}
                  item={item}
                  active={isActive(item.href)}
                  collapsed={false}
                />
              ))}
            </nav>

            <div className="border-t border-gray-100 p-3">
              <ConnectionStatus />
              <button
                onClick={handleLogout}
                className="flex items-center gap-3 w-full px-3 py-2 rounded-xl text-sm text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors"
              >
                <IconLogOut size={18} className="flex-shrink-0" />
                <span>Logout</span>
              </button>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
