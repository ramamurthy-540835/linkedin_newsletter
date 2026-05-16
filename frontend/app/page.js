'use client';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { searchSerp, scrapeProfile, parseJSON, getPosts, getPublishedPosts } from '@/lib/api';
import { callAI } from '@/lib/modelResolver';
import { API_URL } from '@/lib/constants';
import {
  IconFile,
  IconCheckCircle,
  IconLinkedIn,
  IconNewspaper,
  IconLightbulb,
  IconPalette,
  IconSettings,
  IconSparkles,
  IconCreate,
  IconTrending,
  IconBarChart,
  IconImage,
  IconVideo,
  IconLayers,
  IconPoll,
  IconMegaphone,
  IconCalendar,
  IconZap,
  IconTarget,
  IconRefresh,
} from '@/components/icons';

function Toast({ message, type = 'success', duration = 3000 }) {
  const [show, setShow] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShow(false), duration);
    return () => clearTimeout(timer);
  }, [duration]);

  if (!show) return null;

  const bgColor = type === 'error' ? 'bg-red-50 border-red-200' : type === 'warning' ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200';
  const textColor = type === 'error' ? 'text-red-700' : type === 'warning' ? 'text-yellow-700' : 'text-green-700';

  return (
    <div className={`fixed bottom-4 right-4 ${bgColor} ${textColor} border px-4 py-3 rounded-xl shadow-elevated text-sm font-medium z-50 animate-slide-up max-w-sm`}>
      {message}
    </div>
  );
}

function QuickCreateGrid() {
  const router = useRouter();
  const items = [
    { label: 'Text Post', desc: 'Write a post', icon: IconCreate, color: 'from-blue-600 to-blue-500', bg: 'bg-blue-50', text: 'text-blue-600', href: '/create?type=text' },
    { label: 'Image Post', desc: 'AI-generated visual', icon: IconImage, color: 'from-purple-600 to-purple-500', bg: 'bg-purple-50', text: 'text-purple-600', href: '/create?type=image' },
    { label: 'Video Post', desc: 'AI video with Veo', icon: IconVideo, color: 'from-red-600 to-red-500', bg: 'bg-red-50', text: 'text-red-600', href: '/create?type=video' },
    { label: 'Carousel', desc: 'Multi-slide story', icon: IconLayers, color: 'from-amber-600 to-amber-500', bg: 'bg-amber-50', text: 'text-amber-600', href: '/create?type=carousel' },
    { label: 'Poll', desc: 'Engage your audience', icon: IconPoll, color: 'from-green-600 to-green-500', bg: 'bg-green-50', text: 'text-green-600', href: '/create?type=poll' },
    { label: 'Newsletter', desc: 'Long-form content', icon: IconNewspaper, color: 'from-teal-600 to-teal-500', bg: 'bg-teal-50', text: 'text-teal-600', href: '/create?type=newsletter' },
  ];

  return (
    <div>
      <h2 className="section-header mb-4">
        <IconZap size={20} className="text-studio-600" />
        Quick Create
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              onClick={() => router.push(item.href)}
              className="content-card p-4 text-center group cursor-pointer"
            >
              <div className={`w-10 h-10 rounded-xl ${item.bg} flex items-center justify-center mx-auto mb-2 group-hover:scale-110 transition-transform duration-200`}>
                <Icon size={20} className={item.text} />
              </div>
              <div className="text-sm font-semibold text-gray-900">{item.label}</div>
              <div className="text-xs text-gray-500 mt-0.5">{item.desc}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function StatCards({ draftCount, publishedCount, linkedinConnected, linkedinName, topicCount }) {
  const stats = [
    { label: 'Drafts', value: draftCount, icon: IconFile, bg: 'bg-amber-50', text: 'text-amber-600', border: 'border-amber-200' },
    { label: 'Published', value: publishedCount, icon: IconCheckCircle, bg: 'bg-green-50', text: 'text-green-600', border: 'border-green-200' },
    { label: 'Scheduled', value: 0, icon: IconCalendar, bg: 'bg-blue-50', text: 'text-blue-600', border: 'border-blue-200' },
    { label: 'Engagement', value: '-', icon: IconTarget, bg: 'bg-purple-50', text: 'text-purple-600', border: 'border-purple-200' },
    { label: 'LinkedIn', value: linkedinConnected ? (linkedinName ? linkedinName.split(' ')[0] : 'Yes') : 'No', icon: IconLinkedIn, bg: 'bg-linkedin-50', text: 'text-linkedin-600', border: 'border-linkedin-200', small: true },
    { label: 'Topics', value: topicCount, icon: IconTrending, bg: 'bg-rose-50', text: 'text-rose-600', border: 'border-rose-200' },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {stats.map((s) => {
        const Icon = s.icon;
        return (
          <div key={s.label} className="stat-card flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl ${s.bg} flex items-center justify-center flex-shrink-0`}>
              <Icon className={s.text} size={20} />
            </div>
            <div>
              <div className={`font-bold text-gray-900 ${s.small ? 'text-sm' : 'text-xl'}`}>{s.value}</div>
              <div className="text-xs text-gray-500">{s.label}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MyFeed() {
  const [topics, setTopics] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [digest, setDigest] = useState('');
  const [digestLoading, setDigestLoading] = useState(false);
  const [newTopic, setNewTopic] = useState('');
  const [serpKey, setSerpKey] = useState('');
  const [toast, setToast] = useState('');

  const [suggestions, setSuggestions] = useState([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const debounceTimer = useRef(null);
  const inputRef = useRef(null);
  const suggestionsRef = useRef(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('linkedin_topics');
      const t = stored ? JSON.parse(stored) : [];
      setTopics(t);
      setSerpKey(localStorage.getItem('SERP_API_KEY') || '');
      if (t.length > 0 && localStorage.getItem('SERP_API_KEY')) {
        loadFeed(t);
      }
      if (localStorage.getItem('_triggerProfileLoad')) {
        localStorage.removeItem('_triggerProfileLoad');
        setTimeout(() => loadFromProfile(), 100);
      }
    }
  }, []);

  useEffect(() => {
    if (newTopic.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(async () => {
      setSuggestionsLoading(true);
      try {
        const urls = [`${API_URL}/api/config/autocomplete`, `/api/proxy/api/config/autocomplete`];
        let data = null;
        for (const url of urls) {
          try {
            const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ partial: newTopic }) });
            if (res.ok) { data = await res.json(); break; }
          } catch {}
        }
        if (data) {
          setSuggestions(Array.isArray(data.suggestions) ? data.suggestions : []);
          setShowSuggestions(data.suggestions?.length > 0);
          setHighlightedIndex(-1);
        } else {
          setSuggestions([]);
        }
      } catch {
        setSuggestions([]);
      } finally {
        setSuggestionsLoading(false);
      }
    }, 150);
    return () => { if (debounceTimer.current) clearTimeout(debounceTimer.current); };
  }, [newTopic]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target) && inputRef.current && !inputRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) {
      if (e.key === 'Enter') addTopic();
      return;
    }
    switch (e.key) {
      case 'ArrowDown': e.preventDefault(); setHighlightedIndex((prev) => (prev + 1) % suggestions.length); break;
      case 'ArrowUp': e.preventDefault(); setHighlightedIndex((prev) => (prev === -1 ? suggestions.length - 1 : prev - 1)); break;
      case 'Enter': e.preventDefault(); highlightedIndex >= 0 ? selectSuggestion(suggestions[highlightedIndex]) : newTopic.trim() && addTopic(); break;
      case 'Escape': setShowSuggestions(false); break;
    }
  };

  const selectSuggestion = (suggestion) => {
    setNewTopic(suggestion);
    setShowSuggestions(false);
    if (suggestion.trim() && !topics.includes(suggestion.trim())) {
      const updated = [...topics, suggestion.trim()];
      setTopics(updated);
      localStorage.setItem('linkedin_topics', JSON.stringify(updated));
      setNewTopic('');
      if (serpKey) loadFeed(updated);
    }
  };

  const loadFeed = async (topicsToLoad = topics) => {
    if (topicsToLoad.length === 0 || !serpKey) return;
    setLoading(true);
    setResults([]);
    try {
      const settled = await Promise.allSettled(
        topicsToLoad.map((topic) => searchSerp(`${topic} LinkedIn posts news today`, serpKey))
      );
      const allResults = settled.flatMap((r) => r.status === 'fulfilled' ? r.value.results || [] : []);
      setResults(allResults);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const generateDigest = async () => {
    if (results.length === 0) return;
    setDigestLoading(true);
    try {
      const headlines = results.map((r) => `${r.title}: ${r.snippet}`).join('\n\n');
      const userMsg = `Here are today's LinkedIn trending topics and news:\n\n${headlines}\n\nGenerate a 3-bullet morning briefing summarizing the key insights and trends.`;
      const response = await callAI('digest', userMsg, 'You are a LinkedIn content strategist providing morning briefings.');
      setDigest(response);
    } catch (e) {
      setDigest(`Error: ${e.message}`);
    } finally {
      setDigestLoading(false);
    }
  };

  const loadFromProfile = async () => {
    const profileUrl = localStorage.getItem('linkedin_profile_url') || 'https://www.linkedin.com/in/ramavala';
    const localSerpKey = localStorage.getItem('SERP_API_KEY') || '';
    let backendSerpConfigured = false;
    try {
      const configRes = await fetch(`${API_URL}/api/config/status`);
      if (configRes.ok) { const config = await configRes.json(); backendSerpConfigured = config.serp_configured; }
    } catch {}
    const hasSerpKey = localSerpKey.trim() || backendSerpConfigured;
    if (!hasSerpKey) { setToast('Please set SerpAPI key in Settings'); return; }
    try {
      const profile = await scrapeProfile(profileUrl, localSerpKey);
      const existingTopics = new Set(topics);
      let newTopicsAdded = [];
      const candidateTopics = [...(profile.interests || []), ...(profile.skills || [])];
      for (const t of candidateTopics) {
        if (!existingTopics.has(t) && t.trim()) { newTopicsAdded.push(t); existingTopics.add(t); }
      }
      if (newTopicsAdded.length > 0) {
        const updated = [...topics, ...newTopicsAdded];
        setTopics(updated);
        localStorage.setItem('linkedin_topics', JSON.stringify(updated));
        localStorage.setItem('linkedin_profile_data', JSON.stringify(profile));
        await loadFeed(updated);
        setToast(`Added ${newTopicsAdded.length} topic${newTopicsAdded.length !== 1 ? 's' : ''} from your LinkedIn profile`);
      } else {
        setToast('No new topics to add from profile');
      }
    } catch (e) {
      setToast(`Error loading profile: ${e.message}`);
    }
  };

  const addTopic = () => {
    if (newTopic.trim() && !topics.includes(newTopic.trim())) {
      const updated = [...topics, newTopic.trim()];
      setTopics(updated);
      localStorage.setItem('linkedin_topics', JSON.stringify(updated));
      setNewTopic('');
      setShowSuggestions(false);
      if (serpKey) loadFeed(updated);
    }
  };

  const removeTopic = (t) => {
    const updated = topics.filter((x) => x !== t);
    setTopics(updated);
    localStorage.setItem('linkedin_topics', JSON.stringify(updated));
  };

  return (
    <>
      <div className="content-card h-full flex flex-col overflow-hidden">
        <div className="bg-gradient-to-r from-studio-50 to-linkedin-50 border-b border-studio-100 p-4 flex items-center gap-2">
          <IconNewspaper className="text-studio-600" size={20} />
          <h2 className="font-bold text-gray-900">My Feed</h2>
        </div>

        <div className="flex-1 overflow-y-auto flex flex-col">
          <div className="p-4 space-y-3">
            <div className="relative">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <input
                    ref={inputRef}
                    type="text"
                    placeholder="Add a topic..."
                    value={newTopic}
                    onChange={(e) => setNewTopic(e.target.value)}
                    onKeyDown={handleInputKeyDown}
                    onFocus={() => newTopic.length >= 2 && setShowSuggestions(true)}
                    className="input-field pr-8"
                  />
                  {suggestionsLoading && (
                    <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b border-studio-600"></div>
                    </div>
                  )}
                </div>
                <button onClick={addTopic} className="btn-primary !px-4 !py-2" disabled={!newTopic.trim()}>
                  Add
                </button>
              </div>
              {showSuggestions && suggestions.length > 0 && (
                <div ref={suggestionsRef} className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-elevated z-20 overflow-hidden">
                  {suggestions.map((suggestion, index) => (
                    <div key={index} onClick={() => selectSuggestion(suggestion)} className={`px-3 py-2 text-sm cursor-pointer flex items-center gap-2 transition ${index === highlightedIndex ? 'bg-studio-100 text-studio-700' : 'hover:bg-gray-50 text-gray-700'}`}>
                      <IconSparkles size={14} className="text-studio-500" />
                      <span>{suggestion}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {topics.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {topics.map((t) => (
                  <div key={t} className="bg-studio-50 text-studio-700 rounded-full px-3 py-1 text-xs flex items-center gap-2 border border-studio-100">
                    {t}
                    <button onClick={() => removeTopic(t)} className="text-studio-500 hover:text-studio-800 font-bold">x</button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2 pt-1">
              {topics.length > 0 && (
                <button onClick={() => loadFeed(topics)} disabled={loading} className="flex-1 btn-primary !py-2 !text-xs">
                  {loading ? 'Loading...' : 'Reload Feed'}
                </button>
              )}
              <button onClick={loadFromProfile} className="flex-1 px-3 py-2 bg-green-600 text-white rounded-xl text-xs font-semibold hover:bg-green-700 transition">
                From Profile
              </button>
            </div>
          </div>

          {loading && (
            <div className="flex justify-center py-4">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-studio-600"></div>
            </div>
          )}

          {results.length > 0 && (
            <div className="flex-1 flex flex-col overflow-y-auto">
              <div className="p-4 space-y-2 overflow-y-auto">
                {results.slice(0, 10).map((r, i) => (
                  <a key={i} href={r.link} target="_blank" rel="noreferrer" className="block p-3 bg-gray-50 border border-gray-100 rounded-xl hover:bg-studio-50 hover:border-studio-100 transition group">
                    <div className="font-semibold text-xs text-gray-900 line-clamp-2 group-hover:text-studio-700">{r.title}</div>
                    <div className="text-xs text-gray-600 line-clamp-1 mt-1">{r.snippet}</div>
                    <div className="text-xs text-gray-400 mt-1">{r.source || 'Read'}</div>
                  </a>
                ))}
              </div>
              <div className="p-4 border-t border-gray-100 space-y-2">
                <button onClick={generateDigest} disabled={digestLoading} className="w-full btn-primary !py-2 !text-xs">
                  {digestLoading ? 'Generating...' : 'Daily Digest'}
                </button>
                {digest && (
                  <div className="p-3 bg-green-50 border border-green-200 rounded-xl">
                    <div className="text-xs text-gray-800 whitespace-pre-wrap">{digest}</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {!loading && topics.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-gray-400">
              <IconNewspaper size={36} className="text-gray-200 mb-3" />
              <p className="text-sm font-medium text-gray-500">Add topics to get started</p>
              <p className="text-xs text-gray-400 mt-1">Track trending content in your niche</p>
            </div>
          )}
        </div>
      </div>
      {toast && <Toast message={toast} />}
    </>
  );
}

function TopicSuggestions({ onToast }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [profileUrl, setProfileUrl] = useState('');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setProfileUrl(localStorage.getItem('linkedin_profile_url') || 'https://www.linkedin.com/in/ramavala');
    }
  }, []);

  useEffect(() => {
    const onFocus = () => {
      if (typeof window !== 'undefined') {
        setProfileUrl(localStorage.getItem('linkedin_profile_url') || 'https://www.linkedin.com/in/ramavala');
      }
    };
    window.addEventListener('focus', onFocus);
    const interval = setInterval(onFocus, 2000);
    return () => { window.removeEventListener('focus', onFocus); clearInterval(interval); };
  }, []);

  const loadSuggestions = async () => {
    const url = profileUrl || localStorage.getItem('linkedin_profile_url') || 'https://www.linkedin.com/in/ramavala';
    const serpKey = localStorage.getItem('SERP_API_KEY') || '';
    if (!url) { onToast('Please set your LinkedIn profile URL first'); return; }
    setLoading(true);
    try {
      const profile = await scrapeProfile(url, serpKey);
      localStorage.setItem('linkedin_profile_data', JSON.stringify(profile));
      const systemMsg = 'You are a LinkedIn content strategist. Analyze the profile and suggest trending post topics for this week.';
      const userMsg = `Based on this LinkedIn profile:
Name: ${profile.name}
Headline: ${profile.headline}
Bio: ${profile.bio}
Skills: ${profile.skills.join(', ')}
Summary: ${profile.summary}

Suggest 8 high-performing LinkedIn post topics for THIS week. Return ONLY valid JSON array (no markdown), no explanation:
[{"topic": "title", "hook": "engaging first line", "why_trending": "reason", "estimated_engagement": "high|medium"}]`;
      const response = await callAI('suggestions', userMsg, systemMsg);
      const parsed = parseJSON(response);
      setSuggestions(Array.isArray(parsed) ? parsed : []);
    } catch (e) {
      onToast(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const useThisTopic = (topic, hook) => {
    localStorage.setItem('prefill_topic', topic);
    localStorage.setItem('prefill_hook', hook);
    router.push('/create');
  };

  return (
    <div className="content-card h-full flex flex-col overflow-hidden">
      <div className="bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-100 p-4 flex items-center gap-2">
        <IconLightbulb className="text-amber-600" size={20} />
        <h2 className="font-bold text-gray-900">AI Topic Suggestions</h2>
      </div>
      <div className="flex-1 overflow-y-auto flex flex-col">
        <div className="p-4">
          <button onClick={loadSuggestions} disabled={loading} className="w-full btn-primary !py-2.5">
            {loading ? 'Analyzing profile...' : 'Load Suggestions'}
          </button>
          {profileUrl && <p className="text-xs text-gray-400 mt-2 truncate" title={profileUrl}>Profile: {profileUrl.split('/in/')[1] || profileUrl}</p>}
        </div>
        {loading && (
          <div className="flex justify-center py-4">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-studio-600"></div>
          </div>
        )}
        {suggestions.length > 0 && (
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {suggestions.map((s, i) => (
              <div key={i} className="p-3 bg-gray-50 border border-gray-100 rounded-xl hover:bg-studio-50 hover:border-studio-100 transition group">
                <div className="font-semibold text-sm text-gray-900">{s.topic}</div>
                <div className="text-xs text-gray-600 mt-1">{s.hook}</div>
                <div className="flex gap-2 mt-2 justify-between items-center">
                  <div className="flex gap-1">
                    {s.estimated_engagement === 'high' && <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">High</span>}
                    {s.estimated_engagement === 'medium' && <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">Medium</span>}
                    {s.why_trending && <span className="text-xs text-green-600 font-medium">Trending</span>}
                  </div>
                  <button onClick={() => useThisTopic(s.topic, s.hook)} className="text-xs px-3 py-1 bg-studio-600 text-white rounded-lg hover:bg-studio-700 font-medium transition">Use</button>
                </div>
              </div>
            ))}
          </div>
        )}
        {!loading && suggestions.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-gray-400">
            <IconLightbulb size={36} className="text-gray-200 mb-3" />
            <p className="text-sm font-medium text-gray-500">Get AI-powered topic ideas</p>
            <p className="text-xs text-gray-400 mt-1">Based on your LinkedIn profile</p>
          </div>
        )}
      </div>
    </div>
  );
}

function IdeasGenerator({ onToast }) {
  const [topic, setTopic] = useState('');
  const [audience, setAudience] = useState('general');
  const [ideas, setIdeas] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedSlide, setExpandedSlide] = useState(null);

  const generate = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      const systemMsg = 'You are a creative LinkedIn content director creating visual and video content ideas.';
      const userMsg = `For a LinkedIn post about "${topic}" targeting "${audience}", generate content ideas.

Return ONLY valid JSON (no markdown):
{
  "image_prompts": [{"title": "Image 1", "prompt": "detailed prompt for DALL-E/Midjourney", "style": "photorealistic|illustration|3D"}],
  "video_hooks": [{"hook": "first 3 second hook script", "duration": "3s", "format": "Reel|Short"}],
  "carousel": {"title": "5-slide outline", "slides": [{"slide_num": 1, "heading": "title", "bullets": ["point 1", "point 2"]}]}
}`;
      const response = await callAI('suggestions', userMsg, systemMsg);
      const parsed = parseJSON(response);
      setIdeas(parsed);
    } catch (e) {
      onToast(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const copyPrompt = (text) => { navigator.clipboard.writeText(text); onToast('Copied to clipboard'); };

  return (
    <div className="content-card h-full flex flex-col overflow-hidden">
      <div className="bg-gradient-to-r from-purple-50 to-pink-50 border-b border-purple-100 p-4 flex items-center gap-2">
        <IconPalette className="text-purple-600" size={20} />
        <h2 className="font-bold text-gray-900">Ideas Generator</h2>
      </div>
      <div className="flex-1 overflow-y-auto flex flex-col">
        <div className="p-4 space-y-3">
          <input type="text" placeholder='Topic (e.g., "AI Leadership")' value={topic} onChange={(e) => setTopic(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && generate()} className="input-field" />
          <input type="text" placeholder="Audience (e.g., founders, PMs)" value={audience} onChange={(e) => setAudience(e.target.value)} className="input-field" />
          <button onClick={generate} disabled={loading || !topic.trim()} className="w-full btn-primary !py-2.5 gap-2">
            {loading ? 'Generating...' : <><IconPalette size={16} /> Generate Ideas</>}
          </button>
        </div>
        {loading && (
          <div className="flex justify-center py-4">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-studio-600"></div>
          </div>
        )}
        {ideas && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {ideas.image_prompts?.length > 0 && (
              <div>
                <h3 className="font-semibold text-sm mb-2 text-gray-700">Image Prompts</h3>
                <div className="space-y-2">
                  {ideas.image_prompts.map((img, i) => (
                    <div key={i} className="p-3 bg-gray-50 border border-gray-100 rounded-xl text-xs">
                      <div className="font-semibold text-gray-900">{img.title}</div>
                      <div className="text-gray-600 mt-1 font-mono">{img.prompt}</div>
                      <button onClick={() => copyPrompt(img.prompt)} className="mt-2 text-studio-600 hover:text-studio-800 text-xs font-semibold">Copy</button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {ideas.video_hooks?.length > 0 && (
              <div>
                <h3 className="font-semibold text-sm mb-2 text-gray-700">Video Hooks</h3>
                <div className="space-y-2">
                  {ideas.video_hooks.map((vid, i) => (
                    <div key={i} className="p-3 bg-gray-50 border border-gray-100 rounded-xl text-xs">
                      <div className="font-semibold text-gray-900">{vid.duration || '3s'} - {vid.format || 'Reel'}</div>
                      <div className="text-gray-600 mt-1">{vid.hook}</div>
                      <button onClick={() => copyPrompt(vid.hook)} className="mt-2 text-studio-600 hover:text-studio-800 text-xs font-semibold">Copy</button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {ideas.carousel?.slides?.length > 0 && (
              <div>
                <h3 className="font-semibold text-sm mb-2 text-gray-700">Carousel Outline</h3>
                <div className="space-y-1">
                  {ideas.carousel.slides.map((slide, i) => (
                    <div key={i} className="border border-gray-100 rounded-xl overflow-hidden">
                      <button onClick={() => setExpandedSlide(expandedSlide === i ? null : i)} className="w-full p-2.5 bg-studio-50 hover:bg-studio-100 text-left flex justify-between items-center text-xs font-semibold transition">
                        <span>Slide {slide.slide_num || i + 1}: {slide.heading}</span>
                        <span className="text-gray-400">{expandedSlide === i ? '−' : '+'}</span>
                      </button>
                      {expandedSlide === i && (
                        <div className="p-3 bg-gray-50 text-xs space-y-1">
                          {slide.bullets?.map((bullet, j) => (<div key={j} className="text-gray-600">{bullet}</div>))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        {!loading && !ideas && (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-gray-400">
            <IconPalette size={36} className="text-gray-200 mb-3" />
            <p className="text-sm font-medium text-gray-500">Generate content ideas</p>
            <p className="text-xs text-gray-400 mt-1">Images, videos, and carousels</p>
          </div>
        )}
      </div>
    </div>
  );
}

function SetupCard() {
  const router = useRouter();
  return (
    <div className="bg-gradient-to-br from-studio-50 via-white to-linkedin-50 border border-studio-200 rounded-2xl p-8 text-center space-y-4">
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-studio-600 to-linkedin-600 flex items-center justify-center mx-auto">
        <IconSparkles size={32} className="text-white" />
      </div>
      <h2 className="text-2xl font-bold text-gray-900">Welcome to Content Studio</h2>
      <p className="text-gray-600 max-w-md mx-auto">Your AI-powered workspace for creating, scheduling, and publishing LinkedIn content.</p>
      <div className="flex gap-3 justify-center pt-2">
        <a href="/api/auth/linkedin" className="btn-primary !px-6 !py-3">
          <IconLinkedIn size={18} />
          Connect LinkedIn
        </a>
        <button onClick={() => router.push('/admin/settings')} className="btn-secondary !px-6 !py-3">
          <IconSettings size={18} />
          Enter API Keys
        </button>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [toast, setToast] = useState('');
  const [configStatus, setConfigStatus] = useState(null);
  const [showSetupCard, setShowSetupCard] = useState(false);
  const [linkedinConnected, setLinkedinConnected] = useState(false);
  const [linkedinName, setLinkedinName] = useState('');
  const [draftCount, setDraftCount] = useState(0);
  const [publishedCount, setPublishedCount] = useState(0);
  const [topicCount, setTopicCount] = useState(0);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      getPosts().then((posts) => {
        const drafts = Array.isArray(posts) ? posts.filter((p) => p.status === 'draft') : [];
        setDraftCount(drafts.length);
      }).catch(() => setDraftCount(0));

      getPublishedPosts().then((posts) => {
        setPublishedCount(Array.isArray(posts) ? posts.length : 0);
      }).catch(() => setPublishedCount(0));

      const topics = localStorage.getItem('linkedin_topics');
      setTopicCount(topics ? JSON.parse(topics).length : 0);

      fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://10.100.15.44:8007'}/api/config/status`)
        .then(r => r.ok ? r.json() : null)
        .then(config => { if (config) setConfigStatus(config); })
        .catch(() => {});

      const params = new URLSearchParams(window.location.search);
      const name = params.get('name');
      const headline = params.get('headline');
      const profileUrlParam = params.get('profile_url');
      const accessToken = params.get('access_token');
      const authorUrn = params.get('author_urn');
      const oauthError = params.get('oauth_error');

      try {
        const storedOauth = JSON.parse(localStorage.getItem('linkedin_oauth') || '{}');
        if (storedOauth.access_token) { setLinkedinConnected(true); setLinkedinName(storedOauth.name || ''); }
      } catch {}

      if (oauthError) {
        setToast(`LinkedIn connection failed: ${oauthError}`);
        window.history.replaceState({}, document.title, window.location.pathname);
      } else if (accessToken) {
        if (profileUrlParam) localStorage.setItem('linkedin_profile_url', profileUrlParam);
        localStorage.setItem('linkedin_oauth', JSON.stringify({ name, headline, access_token: accessToken, author_urn: authorUrn, profile_url: profileUrlParam }));
        setLinkedinConnected(true);
        setLinkedinName(name || '');
        setToast(`Connected as ${name || 'your profile'}`);
        const topicsStr = localStorage.getItem('linkedin_topics');
        if (!topicsStr || JSON.parse(topicsStr).length === 0) {
          localStorage.setItem('_triggerProfileLoad', 'true');
        }
        window.history.replaceState({}, document.title, window.location.pathname);
      } else {
        const stored = localStorage.getItem('linkedin_profile_url') || 'https://www.linkedin.com/in/ramavala';
        const hasProfile = stored !== null && stored.trim().length > 0;
        const topicsStr = localStorage.getItem('linkedin_topics');
        const hasTopics = topicsStr ? JSON.parse(topicsStr).length > 0 : false;
        if (!hasProfile && !hasTopics) setShowSetupCard(true);
      }
    }
  }, []);

  const localSerpKey = typeof window !== 'undefined' ? localStorage.getItem('SERP_API_KEY') : '';
  const hasAnyKey = localSerpKey || configStatus?.serp_configured;
  if (showSetupCard && !hasAnyKey) {
    return (
      <div className="space-y-6">
        <SetupCard />
        {toast && <Toast message={toast} />}
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Quick Create Grid */}
      <QuickCreateGrid />

      {/* Stat Cards */}
      <StatCards
        draftCount={draftCount}
        publishedCount={publishedCount}
        linkedinConnected={linkedinConnected}
        linkedinName={linkedinName}
        topicCount={topicCount}
      />

      {/* 3-Panel Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4" style={{ minHeight: '480px' }}>
        <MyFeed />
        <TopicSuggestions onToast={setToast} />
        <IdeasGenerator onToast={setToast} />
      </div>

      {toast && <Toast message={toast} />}
    </div>
  );
}
