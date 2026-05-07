'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import Card from '@/components/Card';
import Button from '@/components/Button';
import { getPosts } from '@/lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState({ total: 0, published: 0, drafts: 0, engagement: 0 });
  const [loading, setLoading] = useState(true);
  const [recentPosts, setRecentPosts] = useState([]);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const posts = await getPosts();
      const drafts = posts.filter((p) => p.status === 'draft');
      const published = posts.filter((p) => p.status === 'published');

      setStats({ total: posts.length, published: published.length, drafts: drafts.length, engagement: 0 });
      setRecentPosts(posts.slice(0, 5));
    } catch (error) {
      console.error('Failed to fetch:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-4xl font-bold text-gray-900">Dashboard</h1>
        <Button href="/create" variant="primary">+ Create Post</Button>
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        <Card><div className="text-3xl font-bold text-blue-600">{stats.total}</div><div className="text-gray-600">Total Posts</div></Card>
        <Card><div className="text-3xl font-bold text-green-600">{stats.published}</div><div className="text-gray-600">Published</div></Card>
        <Card><div className="text-3xl font-bold text-yellow-600">{stats.drafts}</div><div className="text-gray-600">Drafts</div></Card>
        <Card><div className="text-3xl font-bold text-purple-600">{stats.engagement}</div><div className="text-gray-600">Engagement</div></Card>
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        <Card className="cursor-pointer hover:shadow-lg transition"><Link href="/create" className="block"><div className="text-4xl mb-3">✨</div><div className="font-bold text-lg">New Post</div><div className="text-sm text-gray-600">Generate & create</div></Link></Card>
        <Card className="cursor-pointer hover:shadow-lg transition"><Link href="/publish" className="block"><div className="text-4xl mb-3">🚀</div><div className="font-bold text-lg">Publish</div><div className="text-sm text-gray-600">Post to LinkedIn</div></Link></Card>
        <Card className="cursor-pointer hover:shadow-lg transition"><Link href="/analytics" className="block"><div className="text-4xl mb-3">📈</div><div className="font-bold text-lg">Analytics</div><div className="text-sm text-gray-600">View engagement</div></Link></Card>
        <Card className="cursor-pointer hover:shadow-lg transition"><Link href="/history" className="block"><div className="text-4xl mb-3">📋</div><div className="font-bold text-lg">History</div><div className="text-sm text-gray-600">All your posts</div></Link></Card>
      </div>

      <Card>
        <h2 className="text-2xl font-bold mb-4">Recent Posts</h2>
        {loading ? (
          <p className="text-gray-600">Loading...</p>
        ) : recentPosts.length === 0 ? (
          <p className="text-gray-600">No posts yet. <Link href="/create" className="text-blue-600 hover:underline">Create one</Link></p>
        ) : (
          <div className="space-y-3">
            {recentPosts.map((post) => (
              <div key={post.id} className="border-b pb-3 last:border-b-0">
                <div className="font-bold text-gray-900">{post.title || post.topic}</div>
                <div className="text-sm text-gray-600">{new Date(post.created_at).toLocaleDateString()} • {post.status === 'published' ? '✅ Published' : '📝 Draft'}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
