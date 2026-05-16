'use client';
import { useState, useEffect } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import LoadingSpinner from '@/components/LoadingSpinner';
import ErrorBanner from '@/components/ErrorBanner';
import SuccessBanner from '@/components/SuccessBanner';
import { IconChevronLeft, IconCompass, IconSearch, IconRefresh } from '@/components/icons';
import {
  getDiscoveryReports,
  getDiscoveryReport,
  getDiscoveryImageUrl,
  publishDiscoveryToLinkedIn,
  publishDiscoveryToDevTo,
  searchWithFreshness,
} from '@/lib/api';

const PROVIDER_COLORS = {
  anthropic: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', badge: 'bg-orange-100 text-orange-800' },
  openai: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', badge: 'bg-green-100 text-green-800' },
  xai: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', badge: 'bg-purple-100 text-purple-800' },
};

const TIME_RANGES = [
  { value: '24h', label: 'Last 24h' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
];

const SOURCE_FILTERS = [
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'news', label: 'News' },
  { value: 'reddit', label: 'Reddit' },
  { value: 'x', label: 'X' },
  { value: 'blogs', label: 'Blogs' },
  { value: 'research', label: 'Research' },
  { value: 'company_news', label: 'Company News' },
];

const SORT_OPTIONS = [
  { value: 'trending', label: 'Trending' },
  { value: 'most_recent', label: 'Most Recent' },
  { value: 'most_shared', label: 'Most Shared' },
  { value: 'high_engagement', label: 'High Engagement' },
];

const SOURCE_ICONS = {
  linkedin: '💼',
  reddit: '🔴',
  x: '𝕏',
  research: '📄',
  web: '🌐',
  news: '📰',
  blogs: '✍️',
};

function FreshnessBadge({ date }) {
  if (!date) return null;
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
      {date}
    </span>
  );
}

function DiscoverTab() {
  const [query, setQuery] = useState('');
  const [timeRange, setTimeRange] = useState('7d');
  const [sources, setSources] = useState([]);
  const [sort, setSort] = useState('trending');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const topics = localStorage.getItem('linkedin_topics');
      if (topics) {
        const parsed = JSON.parse(topics);
        if (parsed.length > 0) {
          setQuery(parsed.slice(0, 3).join(' '));
        }
      }
    }
  }, []);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchWithFreshness({
        query: query.trim(),
        time_range: timeRange,
        sources,
        sort,
      });
      setResults(data.results || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (src) => {
    setSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    );
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-5 space-y-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <IconSearch size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && search()}
              placeholder="Search for trending content..."
              className="input-field !pl-9"
            />
          </div>
          <Button onClick={search} disabled={loading || !query.trim()} variant="primary" loading={loading}>
            Search
          </Button>
        </div>

        <div>
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Freshness</div>
          <div className="flex flex-wrap gap-2">
            {TIME_RANGES.map((tr) => (
              <button
                key={tr.value}
                onClick={() => setTimeRange(tr.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  timeRange === tr.value
                    ? 'bg-studio-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {tr.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Sources</div>
          <div className="flex flex-wrap gap-2">
            {SOURCE_FILTERS.map((sf) => (
              <button
                key={sf.value}
                onClick={() => toggleSource(sf.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  sources.includes(sf.value)
                    ? 'bg-studio-100 text-studio-700 border border-studio-200'
                    : 'bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100'
                }`}
              >
                {SOURCE_ICONS[sf.value] || '📌'} {sf.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 font-medium">Sort by:</span>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
            {SORT_OPTIONS.map((so) => (
              <button
                key={so.value}
                onClick={() => setSort(so.value)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
                  sort === so.value
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {so.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <ErrorBanner message={error} onClose={() => setError(null)} />}

      {loading && <div className="flex justify-center py-6"><LoadingSpinner /></div>}

      {results.length > 0 && (
        <div className="space-y-3">
          <div className="text-sm text-gray-500 font-medium">{results.length} results</div>
          {results.map((item, i) => (
            <a
              key={i}
              href={item.link}
              target="_blank"
              rel="noreferrer"
              className="block bg-white rounded-2xl border border-gray-100 p-4 hover:shadow-card-hover hover:border-gray-200 transition group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-sm">{SOURCE_ICONS[item.source_type] || SOURCE_ICONS.web}</span>
                    <span className="text-xs text-gray-500 uppercase font-medium">{item.source || item.source_type}</span>
                    {item.published_date && <FreshnessBadge date={item.published_date} />}
                  </div>
                  <h3 className="font-semibold text-sm text-gray-900 group-hover:text-studio-700 transition line-clamp-2">
                    {item.title}
                  </h3>
                  <p className="text-xs text-gray-600 mt-1 line-clamp-2">{item.snippet}</p>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && query && (
        <div className="text-center py-12">
          <IconCompass size={40} className="mx-auto text-gray-200 mb-3" />
          <p className="text-sm text-gray-500">No results found. Try adjusting your search or filters.</p>
        </div>
      )}
    </div>
  );
}

function ReportsTab() {
  const [providers, setProviders] = useState([]);
  const [selected, setSelected] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [publishingLi, setPublishingLi] = useState(false);
  const [publishingDevto, setPublishingDevto] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [expandedImage, setExpandedImage] = useState(null);

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDiscoveryReports();
      setProviders(data.providers || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const selectProvider = async (provider) => {
    try {
      setDetailLoading(true);
      setError(null);
      setSuccess(null);
      setSelected(provider);
      const data = await getDiscoveryReport(provider);
      setReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const handlePublishLinkedIn = async () => {
    if (!selected) return;
    try {
      setPublishingLi(true);
      setError(null);
      const result = await publishDiscoveryToLinkedIn(selected);
      setSuccess(`Published to LinkedIn! Post ID: ${result.location || 'OK'}`);
    } catch (err) {
      setError(`LinkedIn publish failed: ${err.message}`);
    } finally {
      setPublishingLi(false);
    }
  };

  const handlePublishDevTo = async () => {
    if (!selected) return;
    try {
      setPublishingDevto(true);
      setError(null);
      const result = await publishDiscoveryToDevTo(selected);
      const url = result.url;
      setSuccess(url ? `Published to Dev.to: ${url}` : 'Published to Dev.to!');
      if (url) setTimeout(() => window.open(url, '_blank'), 1000);
    } catch (err) {
      setError(`Dev.to publish failed: ${err.message}`);
    } finally {
      setPublishingDevto(false);
    }
  };

  const goBack = () => {
    setSelected(null);
    setReport(null);
    setSuccess(null);
    setError(null);
  };

  if (loading) return <div className="flex justify-center py-6"><LoadingSpinner /></div>;

  if (selected && report) {
    const colors = PROVIDER_COLORS[selected] || PROVIDER_COLORS.openai;
    return (
      <div className="space-y-5">
        <div className="flex items-center gap-4">
          <button onClick={goBack} className="text-studio-600 hover:text-studio-700 font-semibold inline-flex items-center gap-1">
            <IconChevronLeft size={16} /> All Reports
          </button>
          <h2 className="text-lg font-bold text-gray-900">{report.display_name} Discovery Report</h2>
        </div>

        {error && <ErrorBanner message={error} onClose={() => setError(null)} />}
        {success && <SuccessBanner message={success} onClose={() => setSuccess(null)} />}

        <div className="grid lg:grid-cols-2 gap-5">
          {report.dashboard_image && (
            <Card>
              <h3 className="font-semibold text-sm text-gray-900 mb-3">Dashboard</h3>
              <img
                src={getDiscoveryImageUrl(selected, report.dashboard_image)}
                alt={`${report.display_name} Dashboard`}
                className="w-full rounded-xl border border-gray-200 cursor-pointer hover:opacity-90 transition"
                onClick={() => setExpandedImage(getDiscoveryImageUrl(selected, report.dashboard_image))}
              />
            </Card>
          )}
          {report.architecture_image && (
            <Card>
              <h3 className="font-semibold text-sm text-gray-900 mb-3">Architecture</h3>
              <img
                src={getDiscoveryImageUrl(selected, report.architecture_image)}
                alt={`${report.display_name} Architecture`}
                className="w-full rounded-xl border border-gray-200 cursor-pointer hover:opacity-90 transition"
                onClick={() => setExpandedImage(getDiscoveryImageUrl(selected, report.architecture_image))}
              />
            </Card>
          )}
        </div>

        {report.linkedin_text && (
          <Card>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm text-gray-900">LinkedIn Post</h3>
              <span className="text-xs text-gray-400">{report.linkedin_text.length} chars</span>
            </div>
            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 whitespace-pre-wrap text-gray-900 max-h-64 overflow-y-auto text-sm">
              {report.linkedin_text}
            </div>
            <Button onClick={handlePublishLinkedIn} disabled={publishingLi} variant="primary" className="mt-4">
              {publishingLi ? 'Publishing...' : 'Publish to LinkedIn'}
            </Button>
          </Card>
        )}

        {report.medium_content && (
          <Card>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm text-gray-900">Article (Dev.to)</h3>
              <span className="text-xs text-gray-400">{report.medium_content.length} chars</span>
            </div>
            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 whitespace-pre-wrap text-gray-900 max-h-80 overflow-y-auto text-sm">
              {report.medium_content}
            </div>
            <Button onClick={handlePublishDevTo} disabled={publishingDevto} variant="primary" className="mt-4">
              {publishingDevto ? 'Publishing...' : 'Publish to Dev.to'}
            </Button>
          </Card>
        )}

        {expandedImage && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-8" onClick={() => setExpandedImage(null)}>
            <div className="max-w-6xl max-h-full overflow-auto">
              <img src={expandedImage} alt="Expanded view" className="w-full rounded-xl" />
            </div>
            <button onClick={() => setExpandedImage(null)} className="absolute top-6 right-6 text-white text-3xl font-bold hover:text-gray-300">&times;</button>
          </div>
        )}
      </div>
    );
  }

  if (selected && detailLoading) {
    return (
      <div className="space-y-5">
        <button onClick={goBack} className="text-studio-600 hover:text-studio-700 font-semibold inline-flex items-center gap-1">
          <IconChevronLeft size={16} /> All Reports
        </button>
        <div className="flex justify-center py-6"><LoadingSpinner /></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && <ErrorBanner message={error} onClose={() => setError(null)} />}

      {providers.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-12 text-center">
          <IconCompass size={40} className="mx-auto text-gray-200 mb-3" />
          <p className="text-gray-600 mb-2 font-medium">No discovery reports found</p>
          <p className="text-sm text-gray-500">
            Run the discovery pipeline first: <code className="bg-gray-100 px-2 py-1 rounded text-xs">python agents/publish_discovery.py</code>
          </p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-3 gap-5">
          {providers.map((p) => {
            const colors = PROVIDER_COLORS[p.name] || PROVIDER_COLORS.openai;
            const badges = [];
            if (p.dashboard_image) badges.push('Dashboard');
            if (p.architecture_image) badges.push('Architecture');
            if (p.linkedin_post_file) badges.push('LinkedIn');
            if (p.medium_article_file || p.medium_draft_file) badges.push('Article');

            return (
              <div key={p.name} className="content-card overflow-hidden">
                <div className={`p-4 ${colors.bg} border-b ${colors.border}`}>
                  <h3 className={`text-lg font-bold ${colors.text}`}>{p.display_name}</h3>
                </div>
                <div className="p-5">
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {badges.map((b) => (
                      <span key={b} className={`px-2 py-0.5 rounded-full text-xs font-semibold ${colors.badge}`}>{b}</span>
                    ))}
                  </div>
                  {p.dashboard_image && (
                    <img
                      src={getDiscoveryImageUrl(p.name, p.dashboard_image)}
                      alt={`${p.display_name} Dashboard`}
                      className="w-full rounded-xl border border-gray-200 mb-4"
                    />
                  )}
                  <Button onClick={() => selectProvider(p.name)} variant="primary" className="w-full">
                    View Report
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function DiscoveryPage() {
  const [activeTab, setActiveTab] = useState('discover');

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Discovery</h1>
        <p className="text-sm text-gray-500 mt-1">Find trending content and explore AI provider reports</p>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        <button
          onClick={() => setActiveTab('discover')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
            activeTab === 'discover'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Discover
        </button>
        <button
          onClick={() => setActiveTab('reports')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
            activeTab === 'reports'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Reports
        </button>
      </div>

      {activeTab === 'discover' ? <DiscoverTab /> : <ReportsTab />}
    </div>
  );
}
