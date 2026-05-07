'use client';
import { useState, useEffect } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import LoadingSpinner from '@/components/LoadingSpinner';
import ErrorBanner from '@/components/ErrorBanner';
import SuccessBanner from '@/components/SuccessBanner';
import LinkedInPreview from '@/components/LinkedInPreview';
import { getDrafts, publishPost, deletePost } from '@/lib/api';

export default function PublishPage() {
  const [drafts, setDrafts] = useState([]);
  const [selectedDraft, setSelectedDraft] = useState(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [publishResult, setPublishResult] = useState(null);

  useEffect(() => {
    fetchDrafts();
  }, []);

  const fetchDrafts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDrafts();
      setDrafts(data);
      if (data.length > 0) setSelectedDraft(data[0]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (draftId) => {
    if (!window.confirm('Delete this draft?')) return;
    try {
      setError(null);
      await deletePost(draftId);
      const updated = drafts.filter((d) => d.id !== draftId);
      setDrafts(updated);
      if (selectedDraft?.id === draftId) {
        setSelectedDraft(updated.length > 0 ? updated[0] : null);
      }
      setSuccess('Draft deleted');
      setTimeout(() => setSuccess(null), 2000);
    } catch (err) {
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
      setSuccess('Posted to LinkedIn');
    } catch (err) {
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

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
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
                      <div className="text-sm text-gray-600 mt-1">{(draft.content || '').slice(0, 140)}...</div>
                      <div className="text-xs text-gray-500 mt-2">
                        Created: {draft.created_at ? new Date(draft.created_at).toLocaleDateString() : 'N/A'}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(draft.id)}
                      className="ml-2 px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded border border-red-200 hover:border-red-400 transition"
                      title="Delete this draft"
                    >
                      Delete
                    </button>
                    <div className="hidden">
                      {/* noop placeholder to keep JSX balanced */}
                    </div>
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
                    <div>{selectedDraft.title}</div>
                  </div>
                )}

                <div>
                  <div className="text-sm font-bold text-gray-600">Content ({selectedDraft.content?.length || 0}/3000 chars)</div>
                  <div className="mt-2 p-3 bg-gray-50 rounded border border-gray-200 whitespace-pre-wrap max-h-56 overflow-y-auto">
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
                    <div>{selectedDraft.cta}</div>
                  </div>
                )}
              </div>

              {publishResult ? (
                <div className="mt-6 p-4 bg-green-50 border-2 border-green-300 rounded-lg space-y-3">
                  <div className="text-lg font-bold text-green-700">Posted to LinkedIn</div>
                  {publishResult.linkedin_url && (
                    <a href={publishResult.linkedin_url} target="_blank" rel="noreferrer" className="inline-block bg-blue-600 text-white px-4 py-2 rounded font-bold hover:bg-blue-700">
                      View on LinkedIn
                    </a>
                  )}
                  {publishResult.linkedin_post_id && (
                    <div className="text-sm text-gray-600">Post ID: {publishResult.linkedin_post_id}</div>
                  )}
                </div>
              ) : (
                <Button onClick={handlePublish} disabled={publishing || !selectedDraft} variant="primary" className="w-full mt-6">
                  {publishing ? 'Publishing...' : 'Publish to LinkedIn'}
                </Button>
              )}
            </Card>
          )}
        </div>

        <div>
          {selectedDraft ? (
            <LinkedInPreview
              title={selectedDraft.title}
              content={selectedDraft.content}
              hashtags={selectedDraft.hashtags}
              cta={selectedDraft.cta}
            />
          ) : (
            <Card><div className="text-center text-gray-600">Select a draft to preview</div></Card>
          )}
        </div>
      </div>
    </div>
  );
}
