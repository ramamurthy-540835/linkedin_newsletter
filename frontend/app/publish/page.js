'use client';
import { useState, useEffect } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import LoadingSpinner from '@/components/LoadingSpinner';
import ErrorBanner from '@/components/ErrorBanner';
import SuccessBanner from '@/components/SuccessBanner';
import { getDrafts, publishPost, deletePost } from '@/lib/api';

export default function PublishPage() {
  const [drafts, setDrafts] = useState([]);
  const [selectedDraft, setSelectedDraft] = useState(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [publishResult, setPublishResult] = useState(null);
  const [pendingDeleteId, setPendingDeleteId] = useState(null);

  useEffect(() => {
    fetchDrafts();
  }, []);

  const fetchDrafts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDrafts();
      setDrafts(data);
      if (data.length > 0) {
        setSelectedDraft(data[0]);
      }
    } catch (err) {
      console.error('Failed to load drafts:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (draftId) => {
    try {
      setError(null);
      await deletePost(draftId);

      const updated = drafts.filter((d) => d.id !== draftId);
      setDrafts(updated);

      if (selectedDraft?.id === draftId) {
        setSelectedDraft(updated.length > 0 ? updated[0] : null);
      }

      setSuccess('✅ Draft deleted');
      setTimeout(() => setSuccess(null), 2000);
    } catch (err) {
      console.error('Delete failed:', err);
      setError(`Failed to delete: ${err.message}`);
    }
  };

  const handlePublish = async () => {
    if (!selectedDraft) {
      setError('Please select a draft');
      return;
    }

    try {
      setPublishing(true);
      setError(null);

      const result = await publishPost(selectedDraft.id);

      setPublishResult(result);
      setSuccess('✅ Post published to LinkedIn!');

      setTimeout(() => {
        if (result.linkedin_url) {
          window.open(result.linkedin_url, '_blank');
        }
      }, 1000);
    } catch (err) {
      console.error('Publish failed:', err);
      setError(err.message);
    } finally {
      setPublishing(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Publish Post</h1>
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Publish Post</h1>

      {error && <ErrorBanner message={error} onClose={() => setError(null)} />}
      {success && <SuccessBanner message={success} onClose={() => setSuccess(null)} />}

      <div className="space-y-6">
        <Card>
          <h2 className="text-xl font-bold mb-4">Select Draft</h2>

          {drafts.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-600 mb-4">No drafts found</p>
              <Button href="/create" variant="primary">Create a Post First</Button>
            </div>
          ) : (
            <div className="space-y-3">
              {drafts.map((draft) => (
                <div
                  key={draft.id}
                  className={`p-4 border-2 rounded-lg transition flex justify-between items-start ${
                    selectedDraft?.id === draft.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-blue-300 bg-white'
                  }`}
                >
                  <div onClick={() => setSelectedDraft(draft)} className="flex-1 cursor-pointer">
                    <div className="font-bold text-gray-900">{draft.title || draft.topic}</div>
                    <div className="text-sm text-gray-600 mt-1 line-clamp-2">{draft.content}</div>
                    <div className="text-xs text-gray-500 mt-2">
                      Created: {draft.created_at ? new Date(draft.created_at).toLocaleDateString() : 'N/A'}
                      {draft.status === 'published' && ' • ✅ Published'}
                    </div>
                  </div>

                  <button
                    onClick={() => setPendingDeleteId(draft.id)}
                    className="ml-2 px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded border border-red-200 hover:border-red-400 transition"
                    title="Delete this draft"
                  >
                    🗑️ Delete
                  </button>
                </div>
              ))}
            </div>
          )}
        </Card>

        {selectedDraft && (
          <Card>
            <h2 className="text-xl font-bold mb-4">Review Post</h2>

            <div className="space-y-4">
              {selectedDraft.title && (
                <div>
                  <div className="text-sm font-bold text-gray-600">Title</div>
                  <div className="text-gray-900">{selectedDraft.title}</div>
                </div>
              )}

              {selectedDraft.topic && (
                <div>
                  <div className="text-sm font-bold text-gray-600">Topic</div>
                  <div className="text-gray-900">{selectedDraft.topic}</div>
                </div>
              )}

              <div>
                <div className="text-sm font-bold text-gray-600">Content ({selectedDraft.content?.length || 0}/3000 chars)</div>
                <div className="mt-2 p-3 bg-gray-50 rounded border border-gray-200 text-gray-900 whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {selectedDraft.content}
                </div>
              </div>

              {selectedDraft.hashtags?.length > 0 && (
                <div>
                  <div className="text-sm font-bold text-gray-600">Hashtags</div>
                  <div className="flex gap-2 flex-wrap mt-2">
                    {selectedDraft.hashtags.map((tag, i) => (
                      <span key={i} className="bg-blue-100 text-blue-800 px-3 py-1 rounded text-sm">{tag}</span>
                    ))}
                  </div>
                </div>
              )}

              {selectedDraft.cta && (
                <div>
                  <div className="text-sm font-bold text-gray-600">Call to Action</div>
                  <div className="text-gray-900">{selectedDraft.cta}</div>
                </div>
              )}
            </div>

            {publishResult ? (
              <div className="mt-6 p-4 bg-green-50 border-2 border-green-300 rounded-lg space-y-3">
                <div className="text-lg font-bold text-green-700">✅ Posted to LinkedIn!</div>
                {publishResult.linkedin_url && (
                  <a
                    href={publishResult.linkedin_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block bg-blue-600 text-white px-4 py-2 rounded font-bold hover:bg-blue-700"
                  >
                    🔗 View on LinkedIn
                  </a>
                )}
                <div className="text-sm text-gray-600">Post ID: {publishResult.linkedin_post_id}</div>
              </div>
            ) : (
              <Button onClick={handlePublish} disabled={publishing || !selectedDraft} variant="primary" className="w-full mt-6">
                {publishing ? '⏳ Publishing...' : '🚀 Publish to LinkedIn'}
              </Button>
            )}
          </Card>
        )}

        {pendingDeleteId && (
          <Card>
            <div className="flex flex-wrap gap-2 items-center justify-between">
              <div className="text-sm font-semibold text-gray-700">Delete this draft?</div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    handleDelete(pendingDeleteId);
                    setPendingDeleteId(null);
                  }}
                  className="px-3 py-1 bg-red-600 text-white rounded text-sm font-semibold"
                >
                  Yes, delete
                </button>
                <button
                  onClick={() => setPendingDeleteId(null)}
                  className="px-3 py-1 bg-gray-200 text-gray-800 rounded text-sm font-semibold"
                >
                  Cancel
                </button>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
