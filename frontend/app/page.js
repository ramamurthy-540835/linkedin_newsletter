'use client';
import { useState, useEffect } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import { getPosts, getPublishedPosts } from '@/lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState({ total: 0, published: 0, drafts: 0, engagement: 0 });
  const [loading, setLoading] = useState(true);
  const [recentPosts, setRecentPosts] = useState([]);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [posts, published] = await Promise.all([getPosts(), getPublishedPosts()]);
      const drafts = posts.filter((p) => p.status === 'draft').length;
      const totalEngagement = published.reduce((sum, p) => sum + ((p.views || 0) + (p.likes || 0) + (p.comments || 0)), 0);
      setStats({ total: posts.length, published: published.length, drafts, engagement: totalEngagement });
      setRecentPosts(posts.slice(0, 5));
    } finally { setLoading(false); }
  };

  return <div className="space-y-6"><div className="flex justify-between items-center"><h1 className="text-3xl font-bold">Dashboard</h1><Button href="/create" variant="primary">+ Create Post</Button></div><div className="grid md:grid-cols-4 gap-4">{['Total Posts','Published','Drafts','Total Engagement'].map((k,i)=><Card key={k}><div className="text-2xl font-bold">{[stats.total,stats.published,stats.drafts,stats.engagement][i]}</div><div className="text-gray-600">{k}</div></Card>)}</div><Card><h2 className="text-xl font-bold mb-4">Recent Posts</h2>{loading ? <p>Loading...</p> : recentPosts.length===0 ? <p className="text-gray-600">No posts yet.</p> : <div className="space-y-2">{recentPosts.map((post)=><div key={post.id} className="border-b pb-2 last:border-b-0"><div className="font-bold">{post.title||post.topic}</div></div>)}</div>}</Card></div>;
}
