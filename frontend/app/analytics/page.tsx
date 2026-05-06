'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/analytics/summary`).then((r) => r.json()).then(setSummary);
  }, []);

  return (
    <main className="container">
      <h1>Analytics Dashboard</h1>
      <div className="card">
        <pre>{JSON.stringify(summary, null, 2)}</pre>
      </div>
    </main>
  );
}
