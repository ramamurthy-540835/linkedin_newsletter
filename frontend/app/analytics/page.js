'use client';
import { useEffect, useState } from 'react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { getPosts, getPublishedPosts } from '@/lib/api';
import { IconEye, IconHeart, IconMessageCircle, IconShare, IconBarChart, IconTrending } from '@/components/icons';

export default function AnalyticsPage() {
  const [publishedPosts, setPublishedPosts] = useState([]);
  const [allPosts, setAllPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [published, posts] = await Promise.all([
          getPublishedPosts(),
          getPosts(),
        ]);
        setPublishedPosts(published);

        const publishedMap = {};
        published.forEach((p) => {
          if (p.post_id) publishedMap[p.post_id] = p;
        });

        const merged = posts.map((post) => {
          const metrics = publishedMap[post.id] || {};
          return {
            ...post,
            views: metrics.views || 0,
            likes: metrics.likes || 0,
            comments: metrics.comments || 0,
            shares: metrics.shares || 0,
            published_at: metrics.published_at || null,
          };
        });

        setAllPosts(merged);
      } catch {
        setPublishedPosts([]);
        setAllPosts([]);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const totals = publishedPosts.reduce(
    (a, p) => ({
      views: a.views + (p.views || 0),
      likes: a.likes + (p.likes || 0),
      comments: a.comments + (p.comments || 0),
      shares: a.shares + (p.shares || 0),
    }),
    { views: 0, likes: 0, comments: 0, shares: 0 }
  );

  const formatDate = (dateStr) => {
    if (!dateStr) return '--';
    try { return new Date(dateStr).toLocaleDateString(); } catch { return '--'; }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">Track your content performance</p>
        </div>
        <LoadingSpinner />
      </div>
    );
  }

  const metricCards = [
    { label: 'Total Views', value: totals.views, icon: IconEye, color: 'from-blue-500 to-blue-600', bg: 'bg-blue-50', text: 'text-blue-600' },
    { label: 'Total Likes', value: totals.likes, icon: IconHeart, color: 'from-red-500 to-red-600', bg: 'bg-red-50', text: 'text-red-600' },
    { label: 'Comments', value: totals.comments, icon: IconMessageCircle, color: 'from-amber-500 to-amber-600', bg: 'bg-amber-50', text: 'text-amber-600' },
    { label: 'Shares', value: totals.shares, icon: IconShare, color: 'from-green-500 to-green-600', bg: 'bg-green-50', text: 'text-green-600' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-sm text-gray-500 mt-1">Track your content performance across LinkedIn</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {metricCards.map((m) => {
          const Icon = m.icon;
          return (
            <div key={m.label} className="bg-white rounded-2xl shadow-card border border-gray-100 p-5 hover:shadow-card-hover transition-all duration-200">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-10 h-10 rounded-xl ${m.bg} flex items-center justify-center`}>
                  <Icon size={20} className={m.text} />
                </div>
                <span className="text-sm text-gray-500 font-medium">{m.label}</span>
              </div>
              <div className="text-3xl font-bold text-gray-900">{m.value.toLocaleString()}</div>
            </div>
          );
        })}
      </div>

      {/* Engagement rate */}
      <div className="bg-gradient-to-r from-studio-50 to-linkedin-50 rounded-2xl border border-studio-100 p-5">
        <div className="flex items-center gap-2 mb-2">
          <IconTrending size={18} className="text-studio-600" />
          <h3 className="font-semibold text-sm text-gray-900">Performance Summary</h3>
        </div>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-gray-900">{allPosts.length}</div>
            <div className="text-xs text-gray-500">Total Posts</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-gray-900">{publishedPosts.length}</div>
            <div className="text-xs text-gray-500">Published</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-gray-900">
              {publishedPosts.length > 0
                ? Math.round((totals.likes + totals.comments + totals.shares) / publishedPosts.length)
                : 0}
            </div>
            <div className="text-xs text-gray-500">Avg. Engagement</div>
          </div>
        </div>
      </div>

      {/* Per-Post Metrics Table */}
      <div className="bg-white rounded-2xl shadow-card border border-gray-100 overflow-hidden">
        <div className="p-5 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Post Performance</h2>
        </div>
        {allPosts.length === 0 ? (
          <div className="text-center py-12">
            <IconBarChart size={40} className="mx-auto text-gray-200 mb-3" />
            <p className="text-gray-500 text-sm">No posts yet. Create your first post to see analytics.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/50">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Title</th>
                  <th className="text-left py-3 px-3 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-3 font-medium text-gray-500">Date</th>
                  <th className="text-right py-3 px-3 font-medium text-gray-500">Views</th>
                  <th className="text-right py-3 px-3 font-medium text-gray-500">Likes</th>
                  <th className="text-right py-3 px-3 font-medium text-gray-500">Comments</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Shares</th>
                </tr>
              </thead>
              <tbody>
                {allPosts.map((post) => (
                  <tr key={post.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition">
                    <td className="py-3 px-4 font-medium text-gray-900 max-w-xs truncate">
                      {post.title || post.topic || 'Untitled'}
                    </td>
                    <td className="py-3 px-3">
                      <span className={post.status === 'published' ? 'badge-published' : 'badge-draft'}>
                        {post.status || 'draft'}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-gray-500">
                      {formatDate(post.published_at || post.created_at)}
                    </td>
                    <td className="py-3 px-3 text-right text-gray-700 font-medium">{post.views}</td>
                    <td className="py-3 px-3 text-right text-gray-700 font-medium">{post.likes}</td>
                    <td className="py-3 px-3 text-right text-gray-700 font-medium">{post.comments}</td>
                    <td className="py-3 px-4 text-right text-gray-700 font-medium">{post.shares}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
