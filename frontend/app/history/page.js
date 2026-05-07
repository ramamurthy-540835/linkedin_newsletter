'use client';
import { useEffect, useState } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import { getPosts, deletePost } from '@/lib/api';

export default function HistoryPage() {
  const [posts, setPosts] = useState([]);
  useEffect(() => { getPosts().then(setPosts).catch(() => setPosts([])); }, []);
  return <div className="space-y-4"><h1 className="text-3xl font-bold">History</h1><Card>{posts.map((p)=><div key={p.id} className="border-b py-2 flex justify-between"><div>{p.title||p.topic}</div><Button variant="danger" size="sm" onClick={async()=>{await deletePost(p.id);setPosts((s)=>s.filter(x=>x.id!==p.id));}}>Delete</Button></div>)}</Card></div>;
}
