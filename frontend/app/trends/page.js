'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Card from '@/components/Card';
import Button from '@/components/Button';
import LoadingSpinner from '@/components/LoadingSpinner';
import ErrorBanner from '@/components/ErrorBanner';
import { IconSparkles, IconTrending } from '@/components/icons';
import { discoverTrends } from '@/lib/api';

const ENGAGEMENT_COLORS = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-gray-100 text-gray-600',
};

export default function TrendsPage() {
  const router = useRouter();
  const [topics, setTopics] = useState([]);
  const [newTopic, setNewTopic] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('linkedin_topics');
      if (stored) {
        setTopics(JSON.parse(stored));
      }
    }
  }, []);

  const addTopic = () => {
    if (newTopic.trim() && !topics.includes(newTopic.trim())) {
      setTopics(prev => [...prev, newTopic.trim()]);
      setNewTopic('');
    }
  };

  const removeTopic = (t) => {
    setTopics(prev => prev.filter(x => x !== t));
  };

  const discover = async () => {
    if (topics.length === 0) {
      setError('Add at least one topic to discover trends');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await discoverTrends({
        topics,
        industries: [],
        keywords: [],
      });
      setResults(data);
    } catch (e) {
      setError(e.message || 'Trend discovery failed');
    } finally {
      setLoading(false);
    }
  };

  const useTopic = (title, hook) => {
    localStorage.setItem('prefill_topic', title);
    localStorage.setItem('prefill_hook', hook || '');
    router.push('/create');
  };

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Trend Engine</h1>
        <p className="text-sm text-gray-500 mt-1">Discover trending topics, viral hooks, and content opportunities powered by AI</p>
      </div>

      <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-5 space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={newTopic}
            onChange={(e) => setNewTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTopic()}
            placeholder="Add a topic, industry, or keyword..."
            className="input-field flex-1"
          />
          <Button onClick={addTopic} disabled={!newTopic.trim()} variant="outline">
            Add
          </Button>
        </div>

        {topics.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {topics.map((t) => (
              <span key={t} className="bg-studio-50 text-studio-700 rounded-full px-3 py-1.5 text-xs font-semibold flex items-center gap-2 border border-studio-100">
                {t}
                <button onClick={() => removeTopic(t)} className="text-studio-500 hover:text-studio-800 font-bold">x</button>
              </span>
            ))}
          </div>
        )}

        <button
          onClick={discover}
          disabled={loading || topics.length === 0}
          className="w-full py-3 rounded-xl text-white font-semibold
            bg-gradient-to-r from-studio-600 to-linkedin-600
            hover:from-studio-700 hover:to-linkedin-700
            disabled:opacity-50 disabled:cursor-not-allowed
            shadow-sm hover:shadow-md transition-all duration-200
            flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Discovering Trends...
            </>
          ) : (
            <>
              <IconSparkles size={18} />
              Discover Trends
            </>
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} onClose={() => setError(null)} />}
      {loading && <div className="flex justify-center py-6"><LoadingSpinner /></div>}

      {results && (
        <div className="space-y-5">
          {results.trending_ideas?.length > 0 && (
            <Card title="Trending Post Ideas" subtitle="Hot topics with high engagement potential">
              <div className="space-y-3">
                {results.trending_ideas.map((idea, i) => (
                  <div key={i} className="p-4 bg-gray-50 border border-gray-100 rounded-xl hover:bg-studio-50 hover:border-studio-100 transition group">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <h4 className="font-semibold text-sm text-gray-900">{idea.title}</h4>
                        <p className="text-xs text-gray-600 mt-1">{idea.hook}</p>
                        {idea.why_trending && (
                          <p className="text-xs text-green-600 mt-1 font-medium">Trending: {idea.why_trending}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {idea.engagement_estimate && (
                          <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${ENGAGEMENT_COLORS[idea.engagement_estimate] || ENGAGEMENT_COLORS.medium}`}>
                            {idea.engagement_estimate}
                          </span>
                        )}
                        <Button onClick={() => useTopic(idea.title, idea.hook)} variant="primary" size="sm">
                          Use
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {results.viral_hooks?.length > 0 && (
            <Card title="Viral Hooks" subtitle="Attention-grabbing opening lines">
              <div className="space-y-2">
                {results.viral_hooks.map((hook, i) => (
                  <div key={i} className="p-3 bg-gray-50 border border-gray-100 rounded-xl flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <p className="text-sm text-gray-900 font-medium">"{hook.hook}"</p>
                      <div className="flex gap-2 mt-1">
                        {hook.format && <span className="text-xs bg-studio-50 text-studio-700 px-2 py-0.5 rounded-full">{hook.format}</span>}
                        {hook.topic && <span className="text-xs text-gray-500">{hook.topic}</span>}
                      </div>
                    </div>
                    <button
                      onClick={() => { navigator.clipboard.writeText(hook.hook); }}
                      className="text-xs text-studio-600 hover:text-studio-800 font-semibold whitespace-nowrap"
                    >
                      Copy
                    </button>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {results.discussion_opportunities?.length > 0 && (
            <Card title="Discussion Opportunities" subtitle="Join active conversations">
              <div className="space-y-2">
                {results.discussion_opportunities.map((disc, i) => (
                  <div key={i} className="p-3 bg-gray-50 border border-gray-100 rounded-xl">
                    <h4 className="font-semibold text-sm text-gray-900">{disc.topic}</h4>
                    <p className="text-xs text-gray-600 mt-1">Angle: {disc.angle}</p>
                    {disc.trending_because && (
                      <p className="text-xs text-green-600 mt-1 font-medium">Why: {disc.trending_because}</p>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {results.breaking_news?.length > 0 && (
            <Card title="Breaking News" subtitle="Timely content opportunities">
              <div className="space-y-2">
                {results.breaking_news.map((news, i) => (
                  <div key={i} className="p-3 bg-red-50 border border-red-200 rounded-xl">
                    <h4 className="font-semibold text-sm text-gray-900">{news.headline}</h4>
                    <p className="text-xs text-gray-700 mt-1">{news.relevance}</p>
                    <p className="text-xs text-studio-600 mt-1 font-medium">Post angle: {news.post_angle}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {results.debate_topics?.length > 0 && (
            <Card title="Debate Topics" subtitle="Spark discussion with these questions">
              <div className="space-y-2">
                {results.debate_topics.map((debate, i) => (
                  <div key={i} className="p-3 bg-gray-50 border border-gray-100 rounded-xl">
                    <h4 className="font-semibold text-sm text-gray-900">{debate.question}</h4>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">{debate.side_a}</div>
                      <div className="p-2 bg-orange-50 border border-orange-200 rounded-lg text-xs text-orange-800">{debate.side_b}</div>
                    </div>
                    {debate.engagement_potential && (
                      <span className={`inline-block mt-2 px-2 py-0.5 rounded-full text-xs font-semibold ${ENGAGEMENT_COLORS[debate.engagement_potential] || ENGAGEMENT_COLORS.medium}`}>
                        {debate.engagement_potential} engagement
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
