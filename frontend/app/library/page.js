'use client';
import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Button from '@/components/Button';
import LoadingSpinner from '@/components/LoadingSpinner';
import { getPosts, deletePost, savePost } from '@/lib/api';
import { getMediaFileUrl } from '@/lib/api';
import {
  IconSearch,
  IconTrash,
  IconFile,
  IconGrid,
  IconList,
  IconCreate,
  IconDuplicate,
  IconArchive,
  IconCalendar,
  IconSparkles,
  IconImage,
  IconVideo,
} from '@/components/icons';

const STATUS_OPTIONS = ['all', 'draft', 'published', 'scheduled', 'failed'];

function StatusBadge({ status }) {
  const map = {
    draft: 'badge-draft',
    published: 'badge-published',
    scheduled: 'badge-scheduled',
    failed: 'badge-failed',
    generating: 'badge-generating',
    archived: 'badge-archived',
  };
  return <span className={map[status] || 'badge-draft'}>{status || 'draft'}</span>;
}

function GridCard({ post, onDelete, onDuplicate, pendingDeleteId, setPendingDeleteId }) {
  const router = useRouter();
  const formatDate = (d) => {
    if (!d) return '--';
    try { return new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }); } catch { return '--'; }
  };

  return (
    <div className="content-card group">
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <StatusBadge status={post.status} />
          <span className="text-xs text-gray-400">{formatDate(post.created_at)}</span>
        </div>
        <h3 className="font-semibold text-sm text-gray-900 line-clamp-2 mb-1.5">
          {post.title || post.topic || 'Untitled'}
        </h3>
        <p className="text-xs text-gray-500 line-clamp-3 mb-3">
          {post.content || 'No content'}
        </p>
        {(post.media?.image?.filename || post.media?.video?.filename) && (
          <div className="flex gap-2 mb-2">
            {post.media?.image?.filename && (
              <span className="inline-flex items-center gap-1 text-[10px] bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded-full font-medium">
                <IconImage size={10} /> Image
              </span>
            )}
            {post.media?.video?.filename && (
              <span className="inline-flex items-center gap-1 text-[10px] bg-red-50 text-red-600 px-1.5 py-0.5 rounded-full font-medium">
                <IconVideo size={10} /> Video
              </span>
            )}
          </div>
        )}
        {post.media?.image?.filename && (
          <div className="mb-3 -mx-4">
            <img src={getMediaFileUrl(post.media.image.filename)} alt="" className="w-full h-32 object-cover" />
          </div>
        )}
        {post.hashtags?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {post.hashtags.slice(0, 3).map((tag, i) => (
              <span key={i} className="text-[10px] bg-studio-50 text-studio-600 px-1.5 py-0.5 rounded-full">{tag}</span>
            ))}
            {post.hashtags.length > 3 && <span className="text-[10px] text-gray-400">+{post.hashtags.length - 3}</span>}
          </div>
        )}
      </div>
      <div className="border-t border-gray-50 px-4 py-2.5 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity">
        {pendingDeleteId === post.id ? (
          <div className="flex items-center gap-2 w-full">
            <span className="text-xs text-gray-600">Delete?</span>
            <button onClick={() => { onDelete(post.id); setPendingDeleteId(null); }}
              className="px-2 py-1 bg-red-600 text-white rounded-lg text-xs font-medium">Yes</button>
            <button onClick={() => setPendingDeleteId(null)}
              className="px-2 py-1 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium">No</button>
          </div>
        ) : (
          <>
            <div className="flex gap-1">
              <button onClick={() => onDuplicate(post)} title="Duplicate"
                className="p-1.5 hover:bg-gray-100 rounded-lg transition text-gray-400 hover:text-gray-700">
                <IconDuplicate size={14} />
              </button>
              <button onClick={() => setPendingDeleteId(post.id)} title="Delete"
                className="p-1.5 hover:bg-red-50 rounded-lg transition text-gray-400 hover:text-red-500">
                <IconTrash size={14} />
              </button>
            </div>
            <button onClick={() => router.push(`/create?topic=${encodeURIComponent(post.topic || '')}`)}
              className="text-xs text-studio-600 hover:text-studio-700 font-medium">
              Edit
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function ListView({ posts, onDelete, onDuplicate, pendingDeleteId, setPendingDeleteId }) {
  const router = useRouter();
  const formatDate = (d) => {
    if (!d) return '--';
    try { return new Date(d).toLocaleDateString(); } catch { return '--'; }
  };

  return (
    <div className="bg-white rounded-2xl shadow-card border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="text-left py-3 px-4 font-medium text-gray-500">Title</th>
              <th className="text-left py-3 px-3 font-medium text-gray-500">Status</th>
              <th className="text-left py-3 px-3 font-medium text-gray-500">Date</th>
              <th className="text-left py-3 px-3 font-medium text-gray-500 hidden md:table-cell">Preview</th>
              <th className="text-right py-3 px-4 font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody>
            {posts.map((post) => (
              <tr key={post.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition">
                <td className="py-3 px-4 font-medium text-gray-900 max-w-xs truncate">
                  {post.title || post.topic || 'Untitled'}
                </td>
                <td className="py-3 px-3">
                  <StatusBadge status={post.status} />
                </td>
                <td className="py-3 px-3 text-gray-500">{formatDate(post.created_at)}</td>
                <td className="py-3 px-3 text-gray-500 max-w-xs truncate hidden md:table-cell">
                  {post.content ? (post.content.length > 80 ? post.content.substring(0, 80) + '...' : post.content) : '--'}
                </td>
                <td className="py-3 px-4 text-right">
                  {pendingDeleteId === post.id ? (
                    <div className="flex items-center justify-end gap-2">
                      <span className="text-xs text-gray-600">Delete?</span>
                      <button onClick={() => { onDelete(post.id); setPendingDeleteId(null); }}
                        className="px-2 py-1 bg-red-600 text-white rounded-lg text-xs font-medium">Yes</button>
                      <button onClick={() => setPendingDeleteId(null)}
                        className="px-2 py-1 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium">No</button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => onDuplicate(post)} title="Duplicate"
                        className="p-1.5 hover:bg-gray-100 rounded-lg transition text-gray-400 hover:text-gray-700">
                        <IconDuplicate size={14} />
                      </button>
                      <button onClick={() => setPendingDeleteId(post.id)} title="Delete"
                        className="p-1.5 hover:bg-red-50 rounded-lg transition text-gray-400 hover:text-red-500">
                        <IconTrash size={14} />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function ContentLibraryPage() {
  const router = useRouter();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [viewMode, setViewMode] = useState('grid');
  const [pendingDeleteId, setPendingDeleteId] = useState(null);

  useEffect(() => {
    loadPosts();
  }, []);

  const loadPosts = async () => {
    setLoading(true);
    try {
      const data = await getPosts();
      setPosts(data);
    } catch {
      setPosts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deletePost(id);
      setPosts(posts.filter((p) => p.id !== id));
      setPendingDeleteId(null);
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const handleDuplicate = async (post) => {
    try {
      await savePost({
        title: `${post.title || post.topic || 'Untitled'} (Copy)`,
        topic: post.topic,
        audience: post.audience || 'general',
        tone: post.tone || 'professional',
        content: post.content,
        hashtags: post.hashtags,
        cta: post.cta,
      });
      await loadPosts();
    } catch (err) {
      console.error('Duplicate failed:', err);
    }
  };

  const filtered = useMemo(() => {
    return posts
      .filter((p) => statusFilter === 'all' || p.status === statusFilter)
      .filter(
        (p) =>
          !search ||
          p.title?.toLowerCase().includes(search.toLowerCase()) ||
          p.topic?.toLowerCase().includes(search.toLowerCase()) ||
          p.content?.toLowerCase().includes(search.toLowerCase())
      )
      .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }, [posts, search, statusFilter]);

  const counts = useMemo(() => ({
    all: posts.length,
    draft: posts.filter(p => p.status === 'draft').length,
    published: posts.filter(p => p.status === 'published').length,
    scheduled: posts.filter(p => p.status === 'scheduled').length,
    failed: posts.filter(p => p.status === 'failed').length,
  }), [posts]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Content Library</h1>
            <p className="text-sm text-gray-500 mt-1">All your posts, drafts, and published content</p>
          </div>
        </div>
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Content Library</h1>
          <p className="text-sm text-gray-500 mt-1">{posts.length} total items</p>
        </div>
        <Button onClick={() => router.push('/create')} variant="primary">
          <IconSparkles size={16} /> New Content
        </Button>
      </div>

      {/* Filters bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="relative w-full sm:w-80">
          <IconSearch size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search content..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field !pl-9"
          />
        </div>

        <div className="flex items-center gap-3">
          {/* Status filters */}
          <div className="flex gap-1 bg-gray-100 rounded-xl p-1">
            {STATUS_OPTIONS.map((tab) => (
              <button
                key={tab}
                onClick={() => setStatusFilter(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  statusFilter === tab
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab === 'all' ? 'All' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                {counts[tab] > 0 && <span className="ml-1 text-gray-400">({counts[tab]})</span>}
              </button>
            ))}
          </div>

          {/* View toggle */}
          <div className="flex gap-0.5 bg-gray-100 rounded-lg p-0.5">
            <button onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-md transition ${viewMode === 'grid' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-400'}`}>
              <IconGrid size={16} />
            </button>
            <button onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-md transition ${viewMode === 'list' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-400'}`}>
              <IconList size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <IconFile size={48} className="mx-auto text-gray-200 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No content found</h3>
          <p className="text-gray-500 mb-6 text-sm">
            {search ? 'Try a different search term' : 'Create your first piece of content'}
          </p>
          {!search && (
            <button onClick={() => router.push('/create')} className="btn-primary">
              <IconSparkles size={16} /> Create Content
            </button>
          )}
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((post) => (
            <GridCard
              key={post.id}
              post={post}
              onDelete={handleDelete}
              onDuplicate={handleDuplicate}
              pendingDeleteId={pendingDeleteId}
              setPendingDeleteId={setPendingDeleteId}
            />
          ))}
        </div>
      ) : (
        <ListView
          posts={filtered}
          onDelete={handleDelete}
          onDuplicate={handleDuplicate}
          pendingDeleteId={pendingDeleteId}
          setPendingDeleteId={setPendingDeleteId}
        />
      )}

      {filtered.length > 0 && (
        <div className="text-center text-xs text-gray-400 pt-2">
          Showing {filtered.length} of {posts.length} items
        </div>
      )}
    </div>
  );
}
