'use client';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { searchSerp, scrapeProfile, parseJSON } from '@/lib/api';
import { callAI } from '@/lib/modelResolver';
import { API_URL } from '@/lib/constants';

function LoadingSpinner() {
  return (
    <div className="flex justify-center py-4">
      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
    </div>
  );
}

function Toast({ message, type = 'success', duration = 3000 }) {
  const [show, setShow] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShow(false), duration);
    return () => clearTimeout(timer);
  }, [duration]);

  if (!show) return null;

  const bgColor = type === 'error' ? 'bg-red-100' : type === 'warning' ? 'bg-yellow-100' : 'bg-green-100';
  const textColor = type === 'error' ? 'text-red-700' : type === 'warning' ? 'text-yellow-700' : 'text-green-700';

  return (
    <div className={`fixed bottom-4 right-4 ${bgColor} ${textColor} px-4 py-3 rounded-lg shadow-lg text-sm font-semibold z-50 animate-fade-in max-w-sm`}>
      {message}
    </div>
  );
}

function MyFeed() {
  const [topics, setTopics] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [digest, setDigest] = useState('');
  const [digestLoading, setDigestLoading] = useState(false);
  const [newTopic, setNewTopic] = useState('');
  const [serpKey, setSerpKey] = useState('');
  const [profileData, setProfileData] = useState(null);
  const [toast, setToast] = useState('');

  // Autocomplete state
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const debounceTimer = useRef(null);
  const inputRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Auto-load on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('linkedin_topics');
      const topics = stored ? JSON.parse(stored) : [];
      setTopics(topics);

      setSerpKey(localStorage.getItem('SERP_API_KEY') || '');

      const profile = localStorage.getItem('linkedin_profile_data');
      if (profile) setProfileData(JSON.parse(profile));

      // Auto-load feed if topics exist
      if (topics.length > 0 && localStorage.getItem('SERP_API_KEY')) {
        loadFeed(topics);
      } else {
        setLoading(false);
      }

      // Check if we should auto-trigger profile load (after OAuth)
      if (localStorage.getItem('_triggerProfileLoad')) {
        localStorage.removeItem('_triggerProfileLoad');
        setTimeout(() => loadFromProfile(), 100);
      }
    }
  }, []);

  // Autocomplete debounce
  useEffect(() => {
    if (newTopic.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    // Clear previous timer
    if (debounceTimer.current) clearTimeout(debounceTimer.current);

    // Set new timer
    debounceTimer.current = setTimeout(async () => {
      setSuggestionsLoading(true);
      try {
        const url = `${API_URL}/api/config/autocomplete`;
        console.log('[Autocomplete] Sending request to:', url, 'partial:', newTopic);

        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ partial: newTopic }),
        });

        console.log('[Autocomplete] Response status:', res.status);

        if (!res.ok) {
          const errText = await res.text();
          console.error('[Autocomplete] Request failed:', res.status, errText);
          setSuggestions([]);
          setSuggestionsLoading(false);
          return;
        }

        const data = await res.json();
        console.log('[Autocomplete] Got data:', data);

        setSuggestions(Array.isArray(data.suggestions) ? data.suggestions : []);
        setShowSuggestions(data.suggestions?.length > 0);
        setHighlightedIndex(-1);
      } catch (e) {
        console.error('[Autocomplete] Client error:', e);
        setSuggestions([]);
      } finally {
        setSuggestionsLoading(false);
      }
    }, 400);

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [newTopic]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(e.target) &&
        inputRef.current &&
        !inputRef.current.contains(e.target)
      ) {
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
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) => (prev + 1) % suggestions.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) => (prev === -1 ? suggestions.length - 1 : prev - 1));
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0) {
          selectSuggestion(suggestions[highlightedIndex]);
        } else if (newTopic.trim()) {
          addTopic();
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        break;
    }
  };

  const selectSuggestion = (suggestion) => {
    setNewTopic(suggestion);
    setShowSuggestions(false);
    // Immediately add the topic
    if (suggestion.trim() && !topics.includes(suggestion.trim())) {
      const updated = [...topics, suggestion.trim()];
      setTopics(updated);
      localStorage.setItem('linkedin_topics', JSON.stringify(updated));
      setNewTopic('');
      // Fetch feed for this topic if SerpAPI key exists
      if (serpKey) {
        loadFeed(updated);
      }
    }
  };

  const loadFeed = async (topicsToLoad = topics) => {
    if (topicsToLoad.length === 0 || !serpKey) return;
    setLoading(true);
    setResults([]);
    const allResults = [];

    for (const topic of topicsToLoad) {
      try {
        const res = await searchSerp(`${topic} LinkedIn posts news today`, serpKey);
        allResults.push(...(res.results || []));
        setResults((prev) => [...prev, ...(res.results || [])]);
      } catch (e) {
        console.error(`Feed error for ${topic}:`, e);
      }
    }
    setLoading(false);
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
    // Use stored profile URL or fallback to default
    const profileUrl = localStorage.getItem('linkedin_profile_url') || 'https://www.linkedin.com/in/ramavala';
    const localSerpKey = localStorage.getItem('SERP_API_KEY') || '';

    // Check backend config status
    let backendSerpConfigured = false;
    try {
      const configRes = await fetch(`${API_URL}/api/config/status`);
      if (configRes.ok) {
        const config = await configRes.json();
        backendSerpConfigured = config.serp_configured;
        console.log('[From Profile] Backend config:', config);
      }
    } catch (e) {
      console.error('[From Profile] Failed to check backend config:', e);
    }

    // Only block if BOTH localStorage and backend are missing SerpAPI key
    const hasSerpKey = localSerpKey.trim() || backendSerpConfigured;
    if (!hasSerpKey) {
      setToast('⚠️ Please set SerpAPI key in ⚙️ Settings');
      return;
    }

    try {
      console.log('[From Profile] Scraping profile:', profileUrl, 'with key:', localSerpKey ? '****' : 'backend');
      // Pass key as param if only in localStorage, backend will use env var if present
      const profile = await scrapeProfile(profileUrl, localSerpKey);
      const existingTopics = new Set(topics);

      // Try to add from interests first, then skills
      let newTopicsAdded = [];
      const candidateTopics = [...(profile.interests || []), ...(profile.skills || [])];

      for (const topic of candidateTopics) {
        if (!existingTopics.has(topic) && topic.trim()) {
          newTopicsAdded.push(topic);
          existingTopics.add(topic);
        }
      }

      if (newTopicsAdded.length > 0) {
        const updated = [...topics, ...newTopicsAdded];
        setTopics(updated);
        localStorage.setItem('linkedin_topics', JSON.stringify(updated));
        localStorage.setItem('linkedin_profile_data', JSON.stringify(profile));
        await loadFeed(updated);
        setToast(`✅ Added ${newTopicsAdded.length} topic${newTopicsAdded.length !== 1 ? 's' : ''} from your LinkedIn profile`);
      } else {
        setToast('⚠️ No new topics to add from profile');
      }
    } catch (e) {
      setToast(`❌ Error loading profile: ${e.message}`);
      console.error(e);
    }
  };

  const addTopic = () => {
    if (newTopic.trim() && !topics.includes(newTopic.trim())) {
      const updated = [...topics, newTopic.trim()];
      setTopics(updated);
      localStorage.setItem('linkedin_topics', JSON.stringify(updated));
      setNewTopic('');
      setShowSuggestions(false);
      // Fetch feed for this topic if SerpAPI key exists
      if (serpKey) {
        loadFeed(updated);
      }
    }
  };

  const removeTopic = (t) => {
    const updated = topics.filter((x) => x !== t);
    setTopics(updated);
    localStorage.setItem('linkedin_topics', JSON.stringify(updated));
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow border border-gray-200 h-full flex flex-col overflow-hidden">
        <div className="sticky top-0 bg-blue-50 border-b border-blue-100 p-4 z-10">
          <h2 className="font-bold text-lg">📰 My Feed</h2>
        </div>

        <div className="flex-1 overflow-y-auto flex flex-col">
          <div className="p-4 space-y-3">
            {/* Topic Input with Autocomplete */}
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm pr-8"
                  />
                  {suggestionsLoading && (
                    <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b border-blue-600"></div>
                    </div>
                  )}
                </div>
                <button
                  onClick={addTopic}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition disabled:opacity-50"
                  disabled={!newTopic.trim()}
                >
                  Add
                </button>
              </div>

              {/* Autocomplete Dropdown */}
              {showSuggestions && suggestions.length > 0 && (
                <div
                  ref={suggestionsRef}
                  className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 overflow-hidden"
                >
                  {suggestions.map((suggestion, index) => (
                    <div
                      key={index}
                      onClick={() => selectSuggestion(suggestion)}
                      className={`px-3 py-2 text-sm cursor-pointer flex items-center gap-2 transition ${
                        index === highlightedIndex
                          ? 'bg-blue-100 text-blue-700'
                          : 'hover:bg-gray-50 text-gray-700'
                      }`}
                    >
                      <span className="text-yellow-500">⚡</span>
                      <span>{suggestion}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Topic Pills */}
            {topics.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {topics.map((t) => (
                  <div key={t} className="bg-blue-100 text-blue-700 rounded-full px-3 py-1 text-xs flex items-center gap-2">
                    {t}
                    <button
                      onClick={() => removeTopic(t)}
                      className="text-blue-600 hover:text-blue-800 font-bold"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              {topics.length > 0 && (
                <button
                  onClick={() => loadFeed(topics)}
                  disabled={loading}
                  className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition"
                >
                  {loading ? 'Loading...' : 'Reload Feed'}
                </button>
              )}
              <button
                onClick={loadFromProfile}
                className="flex-1 px-3 py-2 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 transition"
              >
                📥 From Profile
              </button>
            </div>
          </div>

          {/* Results */}
          {loading && <LoadingSpinner />}

          {results.length > 0 && (
            <div className="flex-1 flex flex-col overflow-y-auto">
              <div className="p-4 space-y-2 overflow-y-auto">
                {results.slice(0, 10).map((r, i) => (
                  <a
                    key={i}
                    href={r.link}
                    target="_blank"
                    rel="noreferrer"
                    className="block p-2 bg-gray-50 border border-gray-200 rounded hover:bg-blue-50 transition group"
                  >
                    <div className="font-semibold text-xs text-gray-900 line-clamp-2 group-hover:text-blue-600">
                      {r.title}
                    </div>
                    <div className="text-xs text-gray-600 line-clamp-1 mt-1">{r.snippet}</div>
                    <div className="text-xs text-gray-500 mt-1">→ {r.source || 'Read'}</div>
                  </a>
                ))}
              </div>

              {/* Digest Section */}
              <div className="p-4 border-t border-gray-200 space-y-2">
                <button
                  onClick={generateDigest}
                  disabled={digestLoading}
                  className="w-full px-3 py-2 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 disabled:opacity-50 transition"
                >
                  {digestLoading ? 'Generating...' : '🗞 Daily Digest'}
                </button>
                {digest && (
                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <div className="text-xs text-gray-800 whitespace-pre-wrap">{digest}</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {!loading && topics.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center p-4 text-center text-gray-500">
              <div className="text-3xl mb-2">📝</div>
              <p className="text-sm">Add topics above to get started</p>
            </div>
          )}
        </div>
      </div>

      {/* Toast Notification */}
      {toast && <Toast message={toast} />}
    </>
  );
}

function TopicSuggestions({ onToast }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [profileUrl, setProfileUrl] = useState('');
  const [serpKey, setSerpKey] = useState('');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setProfileUrl(localStorage.getItem('linkedin_profile_url') || '');
      setSerpKey(localStorage.getItem('SERP_API_KEY') || '');
    }
  }, []);

  const loadSuggestions = async () => {
    if (!profileUrl || !serpKey) {
      onToast('⚠️ Please set your LinkedIn profile URL and SerpAPI key first');
      return;
    }

    setLoading(true);
    try {
      const profile = await scrapeProfile(profileUrl, serpKey);
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
      onToast(`❌ Error: ${e.message}`);
      console.error(e);
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
    <div className="bg-white rounded-lg shadow border border-gray-200 h-full flex flex-col overflow-hidden">
      <div className="sticky top-0 bg-blue-50 border-b border-blue-100 p-4 z-10">
        <h2 className="font-bold text-lg">💡 AI Topic Suggestions</h2>
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col">
        <div className="p-4">
          {profileUrl ? (
            <button
              onClick={loadSuggestions}
              disabled={loading}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {loading ? 'Loading...' : 'Load Suggestions'}
            </button>
          ) : (
            <div className="text-center py-6 text-gray-500">
              <p className="text-sm">Set your LinkedIn profile URL in Settings</p>
            </div>
          )}
        </div>

        {loading && <LoadingSpinner />}

        {suggestions.length > 0 && (
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {suggestions.map((s, i) => (
              <div key={i} className="p-3 bg-gray-50 border border-gray-200 rounded-lg hover:bg-blue-50 transition">
                <div className="font-semibold text-sm text-gray-900">{s.topic}</div>
                <div className="text-xs text-gray-700 mt-1">{s.hook}</div>
                <div className="flex gap-2 mt-2 justify-between items-center">
                  <div className="flex gap-1">
                    {s.estimated_engagement === 'high' && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">🔥 High</span>
                    )}
                    {s.estimated_engagement === 'medium' && (
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded">📈 Medium</span>
                    )}
                    {s.why_trending && <span className="text-xs text-green-600">✓ Trending</span>}
                  </div>
                  <button
                    onClick={() => useThisTopic(s.topic, s.hook)}
                    className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Use
                  </button>
                </div>
              </div>
            ))}
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
      onToast(`❌ Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const copyPrompt = (text) => {
    navigator.clipboard.writeText(text);
    onToast('✓ Copied to clipboard');
  };

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 h-full flex flex-col overflow-hidden">
      <div className="sticky top-0 bg-blue-50 border-b border-blue-100 p-4 z-10">
        <h2 className="font-bold text-lg">🎨 Ideas Generator</h2>
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col">
        <div className="p-4 space-y-3">
          <input
            type="text"
            placeholder='Topic (e.g., "AI Leadership")'
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && generate()}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
          <input
            type="text"
            placeholder="Audience (e.g., founders, PMs)"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
          <button
            onClick={generate}
            disabled={loading || !topic.trim()}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {loading ? 'Generating...' : '🎨 Generate Ideas'}
          </button>
        </div>

        {loading && <LoadingSpinner />}

        {ideas && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Image Prompts */}
            {ideas.image_prompts?.length > 0 && (
              <div>
                <h3 className="font-semibold text-sm mb-2">📸 Image Prompts</h3>
                <div className="space-y-2">
                  {ideas.image_prompts.map((img, i) => (
                    <div key={i} className="p-2 bg-gray-50 border border-gray-200 rounded text-xs">
                      <div className="font-semibold">{img.title}</div>
                      <div className="text-gray-700 mt-1 font-mono text-xs">{img.prompt}</div>
                      <button
                        onClick={() => copyPrompt(img.prompt)}
                        className="mt-2 text-blue-600 hover:text-blue-800 text-xs font-semibold"
                      >
                        📋 Copy
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Video Hooks */}
            {ideas.video_hooks?.length > 0 && (
              <div>
                <h3 className="font-semibold text-sm mb-2">🎬 Video Hooks</h3>
                <div className="space-y-2">
                  {ideas.video_hooks.map((vid, i) => (
                    <div key={i} className="p-2 bg-gray-50 border border-gray-200 rounded text-xs">
                      <div className="font-semibold">{vid.duration || '3s'} - {vid.format || 'Reel'}</div>
                      <div className="text-gray-700 mt-1">{vid.hook}</div>
                      <button
                        onClick={() => copyPrompt(vid.hook)}
                        className="mt-2 text-blue-600 hover:text-blue-800 text-xs font-semibold"
                      >
                        📋 Copy
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Carousel */}
            {ideas.carousel?.slides?.length > 0 && (
              <div>
                <h3 className="font-semibold text-sm mb-2">📊 Carousel Outline</h3>
                <div className="space-y-1">
                  {ideas.carousel.slides.map((slide, i) => (
                    <div key={i} className="border border-gray-200 rounded overflow-hidden">
                      <button
                        onClick={() => setExpandedSlide(expandedSlide === i ? null : i)}
                        className="w-full p-2 bg-blue-50 hover:bg-blue-100 text-left flex justify-between items-center text-xs font-semibold"
                      >
                        <span>
                          Slide {slide.slide_num || i + 1}: {slide.heading}
                        </span>
                        <span>{expandedSlide === i ? '▼' : '▶'}</span>
                      </button>
                      {expandedSlide === i && (
                        <div className="p-2 bg-gray-50 text-xs space-y-1">
                          {slide.bullets?.map((bullet, j) => (
                            <div key={j} className="text-gray-700">
                              • {bullet}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SetupCard() {
  const router = useRouter();
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-8 text-center space-y-4">
      <h2 className="text-2xl font-bold text-blue-900">Welcome to LinkedIn Dashboard</h2>
      <p className="text-blue-700">Get started by connecting your LinkedIn profile and setting up your API keys.</p>
      <div className="flex gap-3 justify-center">
        <a href="/api/auth/linkedin" className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700">
          🔗 Connect LinkedIn
        </a>
        <button
          onClick={() => router.push('/admin/settings')}
          className="px-6 py-3 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700"
        >
          ⚙️ Enter API Keys
        </button>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [showProfile, setShowProfile] = useState(false);
  const [profileUrl, setProfileUrl] = useState('');
  const [toast, setToast] = useState('');
  const [configStatus, setConfigStatus] = useState(null);
  const [showSetupCard, setShowSetupCard] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Check backend config status
      fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://10.100.15.44:8007'}/api/config/status`)
        .then(r => r.ok ? r.json() : null)
        .then(config => {
          if (config) setConfigStatus(config);
        })
        .catch(e => console.error('Config check failed:', e));

      // Check for OAuth callback query params
      const params = new URLSearchParams(window.location.search);
      const name = params.get('name');
      const headline = params.get('headline');
      const profileUrlParam = params.get('profile_url');
      const accessToken = params.get('access_token');

      if (profileUrlParam && accessToken) {
        // OAuth completed successfully
        localStorage.setItem('linkedin_profile_url', profileUrlParam);
        localStorage.setItem('linkedin_oauth', JSON.stringify({
          name,
          headline,
          access_token: accessToken,
          profile_url: profileUrlParam,
        }));
        setProfileUrl(profileUrlParam);
        setToast(`✅ Connected as ${name || 'your profile'}`);

        // Auto-trigger "From Profile" if no topics yet
        const topics = localStorage.getItem('linkedin_topics');
        if (!topics || JSON.parse(topics).length === 0) {
          localStorage.setItem('_triggerProfileLoad', 'true');
        }

        // Clean up URL params
        window.history.replaceState({}, document.title, window.location.pathname);
      } else {
        const stored = localStorage.getItem('linkedin_profile_url') || 'https://www.linkedin.com/in/ramavala';
        setProfileUrl(stored);

        // Check if setup is needed: only show if NO profile AND NO topics
        const hasProfile = stored !== null && stored.trim().length > 0;
        const topics = localStorage.getItem('linkedin_topics');
        const hasTopics = topics ? JSON.parse(topics).length > 0 : false;

        console.log('[Dashboard] Setup check - profile:', hasProfile, 'topics:', hasTopics);

        // Don't show setup card if we have profile or topics
        if (!hasProfile && !hasTopics) {
          setShowSetupCard(true);
        }
      }
    }
  }, []);

  const changeProfile = (newUrl) => {
    localStorage.setItem('linkedin_profile_url', newUrl);
    setProfileUrl(newUrl);
    setShowProfile(false);
  };

  // Only show setup card if BOTH missing: no profile AND no SerpAPI key anywhere
  const localSerpKey = typeof window !== 'undefined' ? localStorage.getItem('SERP_API_KEY') : '';
  const hasAnyKey = localSerpKey || configStatus?.serp_configured;
  if (showSetupCard && !hasAnyKey) {
    return (
      <div className="space-y-4">
        <h1 className="text-3xl font-bold text-gray-900">LinkedIn Dashboard</h1>
        <SetupCard />
        {toast && <Toast message={toast} />}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with Account */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">LinkedIn Dashboard</h1>
        <div className="relative">
          <button
            onClick={() => setShowProfile(!showProfile)}
            className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm font-semibold hover:bg-blue-200"
          >
            👤 Account
          </button>
          {showProfile && (
            <div className="absolute right-0 top-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg p-4 w-64 z-20">
              <label className="block text-sm font-semibold mb-2">LinkedIn Profile URL</label>
              <input
                type="text"
                placeholder="https://www.linkedin.com/in/yourname"
                defaultValue={profileUrl}
                onChange={(e) => changeProfile(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm mb-3"
              />
              <button
                onClick={() => setShowProfile(false)}
                className="w-full px-3 py-2 bg-blue-600 text-white rounded text-sm font-semibold hover:bg-blue-700"
              >
                Done
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 3-Panel Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 h-[600px]">
        <MyFeed />
        <TopicSuggestions onToast={setToast} />
        <IdeasGenerator onToast={setToast} />
      </div>

      {/* Global Toast */}
      {toast && <Toast message={toast} />}
    </div>
  );
}
