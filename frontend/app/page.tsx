import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="container">
      <h1>LinkedIn Post Agent</h1>
      <p>Create, optimize, schedule, and track LinkedIn posts.</p>
      <div className="card">
        <p><Link href="/draft">Draft Composer</Link></p>
        <p><Link href="/scheduled">Scheduled Posts</Link></p>
        <p><Link href="/analytics">Analytics Dashboard</Link></p>
      </div>
    </main>
  );
}
