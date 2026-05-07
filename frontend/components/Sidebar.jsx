'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
const items=[['/','Dashboard'],['/create','Create'],['/publish','Publish'],['/analytics','Analytics'],['/history','History'],['/admin/settings','Admin']];
export default function Sidebar(){const p=usePathname();return <aside className="w-64 bg-white border-r p-4 hidden md:block"><nav className="space-y-2">{items.map(([href,label])=><Link key={href} href={href} className={`block px-3 py-2 rounded ${p===href?'bg-blue-100 text-blue-700':'hover:bg-gray-100'}`}>{label}</Link>)}</nav></aside>;}
