'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import {
  IconMenu,
  IconPlus,
  IconLinkedIn,
  IconSettings,
  IconSparkles,
  IconQueue,
} from '@/components/icons';

const TITLES = {
  '/': 'Dashboard',
  '/create': 'Create Content',
  '/publish': 'Publish Queue',
  '/analytics': 'Analytics',
  '/library': 'Content Library',
  '/discovery': 'Discovery',
  '/trends': 'Trends',
  '/admin/settings': 'Settings',
};

export default function Header({ onMobileMenuToggle, cartCount = 0, onCartToggle }) {
  const pathname = usePathname();
  const [showDropdown, setShowDropdown] = useState(false);
  const [connected, setConnected] = useState(false);
  const [name, setName] = useState('');
  const [headline, setHeadline] = useState('');
  const [linkedinAuthUrl, setLinkedinAuthUrl] = useState('');
  const dropdownRef = useRef(null);

  const pageTitle = TITLES[pathname] || 'Content Studio';
  const firstInitial = name ? name.charAt(0).toUpperCase() : '?';

  useEffect(() => {
    try {
      const raw = localStorage.getItem('linkedin_oauth');
      if (raw) {
        const data = JSON.parse(raw);
        setConnected(!!data.access_token);
        setName(data.name || '');
        setHeadline(data.headline || '');
      }
    } catch {
      // ignore
    }

    setLinkedinAuthUrl(
      `${window.location.protocol}//${window.location.hostname}:8007/api/auth/linkedin`
    );
  }, []);

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    }
    if (showDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showDropdown]);

  return (
    <header className="sticky top-0 z-20 bg-white/80 backdrop-blur-md border-b border-gray-100 px-4 lg:px-6 h-14 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button
          onClick={onMobileMenuToggle}
          className="md:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <IconMenu size={20} className="text-gray-600" />
        </button>
        <h1 className="text-lg font-semibold text-gray-900">{pageTitle}</h1>
      </div>

      <div className="flex items-center gap-3">
        <Link
          href="/create"
          className="hidden sm:flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-studio-600 to-linkedin-600 text-white rounded-lg text-sm font-medium hover:from-studio-700 hover:to-linkedin-700 transition-all duration-200 shadow-sm"
        >
          <IconSparkles size={15} />
          New Content
        </Link>

        <button
          onClick={onCartToggle}
          className="relative p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="Draft Cart"
        >
          <IconQueue size={18} className="text-gray-600" />
          {cartCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full px-1">
              {cartCount > 99 ? '99+' : cartCount}
            </span>
          )}
        </button>

        <div
          className={`w-2.5 h-2.5 rounded-full ${
            connected ? 'bg-green-500' : 'bg-amber-400'
          }`}
          title={connected ? 'LinkedIn Connected' : 'Not Connected'}
        />

        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="w-8 h-8 rounded-full bg-gradient-to-br from-studio-100 to-linkedin-100 text-studio-700 font-semibold text-sm flex items-center justify-center hover:from-studio-200 hover:to-linkedin-200 transition-colors"
          >
            {firstInitial}
          </button>

          {showDropdown && (
            <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-xl shadow-elevated border border-gray-100 py-2 animate-fade-in">
              <div className="px-4 py-2 border-b border-gray-100">
                <div className="font-semibold text-sm text-gray-900">
                  {name || 'Not signed in'}
                </div>
                {headline && (
                  <div className="text-xs text-gray-500 truncate">{headline}</div>
                )}
              </div>

              <a
                href={linkedinAuthUrl}
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <IconLinkedIn size={16} />
                {connected ? 'Reconnect LinkedIn' : 'Connect LinkedIn'}
              </a>

              <Link
                href="/admin/settings"
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                onClick={() => setShowDropdown(false)}
              >
                <IconSettings size={16} />
                Settings
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
