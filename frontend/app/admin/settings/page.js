'use client';
import { useEffect, useState } from 'react';
import Card from '@/components/Card';
import { getPlatformCredentials } from '@/lib/api';

export default function AdminSettingsPage() {
  const [data, setData] = useState({});
  useEffect(() => { getPlatformCredentials().then(setData).catch(() => setData({})); }, []);
  return <div className="space-y-4"><h1 className="text-3xl font-bold">Platform Credentials</h1><Card><pre className="text-sm overflow-auto">{JSON.stringify(data,null,2)}</pre></Card></div>;
}
