'use client';
import { useEffect, useState } from 'react';
import Card from '@/components/Card';
import { getPublishedPosts } from '@/lib/api';

export default function AnalyticsPage() {
  const [posts, setPosts] = useState([]);
  useEffect(() => { getPublishedPosts().then(setPosts).catch(() => setPosts([])); }, []);
  const totals = posts.reduce((a,p)=>({views:a.views+(p.views||0),likes:a.likes+(p.likes||0),comments:a.comments+(p.comments||0),shares:a.shares+(p.shares||0)}),{views:0,likes:0,comments:0,shares:0});
  return <div className="space-y-4"><h1 className="text-3xl font-bold">Analytics</h1><div className="grid md:grid-cols-4 gap-4"><Card>{totals.views} Views</Card><Card>{totals.likes} Likes</Card><Card>{totals.comments} Comments</Card><Card>{totals.shares} Shares</Card></div></div>;
}
