'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const MENU_ITEMS = [
  { href: '/', label: 'Dashboard', icon: '🏠' },
  { href: '/create', label: 'Create', icon: '✨' },
  { href: '/publish', label: 'Publish', icon: '🚀' },
  { href: '/analytics', label: 'Analytics', icon: '📈' },
  { href: '/history', label: 'History', icon: '📋' },
  { href: '/admin/settings', label: 'Admin', icon: '⚙️' }
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 p-6 flex-col hidden md:flex">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">LinkedIn</h1>
        <p className="text-sm text-gray-600">Post Generator</p>
      </div>

      <nav className="space-y-2 flex-1">
        {MENU_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`block px-4 py-2 rounded-lg transition ${
              pathname === item.href
                ? 'bg-blue-100 text-blue-600 font-bold'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            {item.icon} {item.label}
          </Link>
        ))}
      </nav>

      <div className="border-t pt-4">
        <button className="w-full px-4 py-2 text-gray-700 hover:bg-red-50 rounded-lg transition text-left">
          Logout
        </button>
      </div>
    </aside>
  );
}
