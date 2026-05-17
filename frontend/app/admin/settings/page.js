'use client';

import { useEffect, useMemo, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { scrapeProfile, searchSerp } from '@/lib/api';
import { ToastProvider, useToast } from '@/app/components/Toast';
import { API_URL } from '@/lib/constants';
import { IconSearch, IconSparkles, IconSettings, IconLinkedIn } from '@/components/icons';

const USE_CASE_LABELS = {
  feed: 'Feed Search',
  digest: 'Daily Digest',
  suggestions: 'Topic Suggest',
  ideas: 'Post Ideas',
  images: 'Image Ideas',
  video: 'Video Ideas',
  post_generation: 'Post Generate',
};

const apiPost = async (path, payload) => {
  const opts = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  };
  try {
    const res = await fetch(`${API_URL}${path}`, opts);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    try {
      const res = await fetch(`/api/proxy${path}`, opts);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      return await res.json();
    } catch (proxyErr) {
      throw e;
    }
  }
};

const getModelDisplayName = (modelId, allModels) => {
  const all = [
    ...(allModels.google || []),
    ...(allModels.anthropic || []),
    ...(allModels.openai || [])
  ];
  return all.find(m => m.model_id === modelId)?.display_name || modelId;
};

const ModelDropdown = ({ useCase, currentModelId, allModels, onSelect, onClose }) => {
  const googleModels = (allModels.google || []).filter(m =>
    m.use_case.includes(useCase) || m.use_case.includes('chat')
  );
  const anthropicModels = (allModels.anthropic || []).filter(m =>
    m.use_case.includes(useCase) || m.use_case.includes('chat')
  );
  const openaiModels = allModels.openai || [];

  return (
    <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-gray-100 rounded-xl shadow-card min-w-72 max-h-96 overflow-y-auto">
      {googleModels.length > 0 && (
        <>
          <div className="px-4 py-2 text-xs font-bold text-blue-600 uppercase bg-blue-50 border-b rounded-t-xl">
            Google / Gemini
          </div>
          {googleModels.map(m => (
            <div key={m.model_id} onClick={() => { onSelect(m.model_id); onClose(); }}
              className={`px-4 py-2 cursor-pointer text-sm border-b hover:bg-blue-50 flex justify-between items-center transition
                ${m.model_id === currentModelId ? 'bg-blue-100 font-semibold' : ''}`}>
              <div>
                <div className="font-medium">{m.display_name}</div>
                <div className="text-xs text-gray-500">{m.notes}</div>
              </div>
              {m.model_id === currentModelId && <span className="text-blue-600 font-bold">&#10003;</span>}
            </div>
          ))}
        </>
      )}

      {anthropicModels.length > 0 && (
        <>
          <div className="px-4 py-2 text-xs font-bold text-amber-700 uppercase bg-amber-50 border-b">
            Anthropic / Claude
          </div>
          {anthropicModels.map(m => (
            <div key={m.model_id} onClick={() => { onSelect(m.model_id); onClose(); }}
              className={`px-4 py-2 cursor-pointer text-sm border-b hover:bg-amber-50 flex justify-between items-center transition
                ${m.model_id === currentModelId ? 'bg-amber-100 font-semibold' : ''}`}>
              <div>
                <div className="font-medium">{m.display_name}</div>
                <div className="text-xs text-gray-500">{m.notes}</div>
              </div>
              {m.model_id === currentModelId && <span className="text-amber-700 font-bold">&#10003;</span>}
            </div>
          ))}
        </>
      )}

      <div className="px-4 py-2 text-xs font-bold text-gray-500 uppercase bg-gray-100 border-b">
        OpenAI (locked)
      </div>
      {openaiModels.map(m => (
        <div key={m.model_id} title="Requires OPENAI_API_KEY in backend .env"
          className="px-4 py-2 text-sm border-b opacity-50 cursor-not-allowed">
          <div className="font-medium">{m.display_name}</div>
          <div className="text-xs text-gray-500">Requires OPENAI_API_KEY</div>
        </div>
      ))}
    </div>
  );
};

function SettingsContent() {
  const { push } = useToast();
  const params = useSearchParams();
  const [serpKey, setSerpKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showGemini, setShowGemini] = useState(false);
  const [testStatus, setTestStatus] = useState('');
  const [models, setModels] = useState({ google: [], anthropic: [], openai: [] });
  const [activeTab, setActiveTab] = useState('google');
  const [modelAssignments, setModelAssignments] = useState({});
  const [geminiTestStatus, setGeminiTestStatus] = useState('');
  const [geminiEnvStatus, setGeminiEnvStatus] = useState('');
  const [linkedinProfileUrl, setLinkedinProfileUrl] = useState('');
  const [openDropdown, setOpenDropdown] = useState(null);

  useEffect(() => {
    const init = async () => {
      setSerpKey(localStorage.getItem('SERP_API_KEY') || '');
      setGeminiKey(localStorage.getItem('GEMINI_API_KEY') || '');
      setLinkedinProfileUrl(localStorage.getItem('linkedin_profile_url') || '');
      try { setModelAssignments(JSON.parse(localStorage.getItem('model_assignments') || '{}')); } catch {}

      const [mRes, rRes, sRes] = await Promise.allSettled([
        fetch(`${API_URL}/api/models`).then((r) => r.json()),
        fetch(`${API_URL}/api/models/recommend?use_case=general`).then((r) => r.json()),
        fetch(`${API_URL}/api/config/status`).then((r) => r.json()),
      ]);
      if (mRes.status === 'fulfilled') setModels(mRes.value || { google: [], anthropic: [], openai: [] });
      if (rRes.status === 'fulfilled') localStorage.setItem('ai_model', rRes.value?.model_id || 'models/gemini-2.5-flash');
      if (sRes.status === 'fulfilled' && sRes.value?.gemini_source === 'env') setGeminiEnvStatus('Configured in .env (secure)');
    };
    init();
    if (params.get('oauth') === 'success') push('LinkedIn connected', 'success');
  }, [params, push]);

  const saveSerpKey = () => { localStorage.setItem('SERP_API_KEY', serpKey.trim()); push('SerpAPI key saved', 'success'); };
  const saveGeminiKey = async () => {
    try {
      localStorage.setItem('GEMINI_API_KEY', geminiKey.trim());
      await apiPost('/api/config/keys', { gemini_api_key: geminiKey.trim() });
      push('Gemini key saved', 'success');
    } catch (e) {
      push(`Failed to save Gemini key: ${e.message}`, 'error');
    }
  };

  const testSerpConnection = async () => {
    try { const res = await searchSerp('LinkedIn', serpKey.trim()); setTestStatus(`Working! Found ${res?.results?.length || 0} results`); }
    catch (e) { setTestStatus(`Failed: ${e.message}`); }
  };

  const testGemini = async () => {
    setGeminiTestStatus('Testing...');
    try {
      const data = await apiPost('/api/ai/generate', { model: 'models/gemini-2.5-flash', prompt: 'Say OK', system: '' });
      setGeminiTestStatus(String(data.text || '').toUpperCase().includes('OK') ? 'Working' : 'Failed');
    } catch (e) { setGeminiTestStatus(`Failed: ${e.message}`); }
  };

  const providerModels = models[activeTab] || [];
  const assignmentRows = useMemo(() => Object.keys(USE_CASE_LABELS), []);

  const setAssignment = (useCase, modelId) => {
    const next = { ...modelAssignments, [useCase]: modelId };
    setModelAssignments(next);
    localStorage.setItem('model_assignments', JSON.stringify(next));
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <IconSettings size={28} className="text-gray-600" /> Settings
        </h1>
      </div>

      {/* SerpAPI Section */}
      <section className="bg-white border border-gray-100 rounded-xl shadow-card p-6 space-y-3">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <IconSearch size={20} className="text-gray-600" /> SerpAPI
        </h2>
        <div className="flex gap-2">
          <input
            type={showPassword ? 'text' : 'password'}
            value={serpKey}
            onChange={(e) => setSerpKey(e.target.value)}
            className="flex-1 border border-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-linkedin-500"
          />
          <button
            onClick={() => setShowPassword(!showPassword)}
            className="px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
          >
            {showPassword ? 'Hide' : 'Show'}
          </button>
        </div>
        <div className="flex gap-2">
          <button onClick={saveSerpKey} className="px-4 py-2 bg-linkedin-600 hover:bg-linkedin-700 text-white rounded-lg font-semibold transition">Save</button>
          <button onClick={testSerpConnection} className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-semibold transition">Test</button>
        </div>
        {testStatus && <div className="text-sm text-gray-700">{testStatus}</div>}
      </section>

      {/* Gemini Section */}
      <section className="bg-white border border-gray-100 rounded-xl shadow-card p-6 space-y-3">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <IconSparkles size={20} className="text-purple-600" /> Gemini API Key
        </h2>
        {geminiEnvStatus && <div className="text-green-700 text-sm">{geminiEnvStatus}</div>}
        <div className="flex gap-2">
          <input
            type={showGemini ? 'text' : 'password'}
            value={geminiKey}
            onChange={(e) => setGeminiKey(e.target.value)}
            className="flex-1 border border-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-linkedin-500"
          />
          <button
            onClick={() => setShowGemini(!showGemini)}
            className="px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
          >
            {showGemini ? 'Hide' : 'Show'}
          </button>
        </div>
        <div className="flex gap-2">
          <button onClick={saveGeminiKey} className="px-4 py-2 bg-linkedin-600 hover:bg-linkedin-700 text-white rounded-lg font-semibold transition">Save</button>
          <button onClick={testGemini} className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-semibold transition">Test</button>
        </div>
        {geminiTestStatus && <div className="text-sm text-gray-700">{geminiTestStatus}</div>}
      </section>

      {/* Model Selector Section */}
      <section className="bg-white border border-gray-100 rounded-xl shadow-card p-6 space-y-3">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <IconSettings size={20} className="text-gray-600" /> Model Selector
        </h2>
        <div className="flex gap-2">
          {['google', 'anthropic', 'openai'].map((t) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`px-3 py-2 rounded-lg border font-semibold text-sm transition ${
                activeTab === t
                  ? 'bg-linkedin-600 text-white border-linkedin-600'
                  : 'bg-white border-gray-200 hover:bg-gray-50'
              }`}
            >
              {t === 'google'
                ? `Google (${models.google?.length || 0})`
                : t === 'anthropic'
                ? `Anthropic (${models.anthropic?.length || 0})`
                : `OpenAI (${models.openai?.length || 0})`}
            </button>
          ))}
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          {providerModels.map((m) => (
            <div key={m.model_id} className="border border-gray-100 rounded-xl shadow-card p-4">
              <div className="flex justify-between items-start">
                <div className="font-bold text-gray-900">{m.display_name}</div>
                {m.is_default && (
                  <span className="text-xs border border-linkedin-200 px-2 py-0.5 rounded-lg bg-linkedin-50 text-linkedin-700 font-semibold">
                    Default
                  </span>
                )}
              </div>
              <div className="text-sm text-gray-600 mt-1">{m.notes}</div>
              <div className="text-xs mt-2 text-gray-500">
                Speed: {'●'.repeat(m.speed_score || 1)}{'○'.repeat(3 - (m.speed_score || 1))} | Cost: {'$'.repeat(m.cost_tier || 1)}{'□'.repeat(3 - (m.cost_tier || 1))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Per-use-case Model Assignment */}
      <section className="bg-white border border-gray-100 rounded-xl shadow-card p-6 space-y-3">
        <h2 className="text-xl font-bold">Per-use-case model assignment</h2>
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="text-left py-2">Feature</th>
              <th className="text-left py-2">Current Model</th>
              <th className="text-left py-2">Change</th>
            </tr>
          </thead>
          <tbody>
            {assignmentRows.map((k) => (
              <tr key={k} className="border-t relative hover:bg-gray-50 transition">
                <td className="py-2">{USE_CASE_LABELS[k]}</td>
                <td className="font-medium">{getModelDisplayName(modelAssignments[k] || 'models/gemini-2.5-flash', models)}</td>
                <td className="relative">
                  <button
                    onClick={() => setOpenDropdown(openDropdown === k ? null : k)}
                    className="px-3 py-1 border border-gray-200 rounded-lg bg-gray-50 hover:bg-gray-100 text-xs font-medium transition"
                  >
                    Change &#9660;
                  </button>
                  {openDropdown === k && (
                    <ModelDropdown
                      useCase={k}
                      currentModelId={modelAssignments[k] || 'models/gemini-2.5-flash'}
                      allModels={models}
                      onSelect={(mid) => setAssignment(k, mid)}
                      onClose={() => setOpenDropdown(null)}
                    />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* LinkedIn Section */}
      <section className="bg-white border border-gray-100 rounded-xl shadow-card p-6">
        <h2 className="text-xl font-bold flex items-center gap-2 mb-3">
          <IconLinkedIn size={20} className="text-linkedin-600" /> LinkedIn
        </h2>
        <a
          href={`${API_URL}/api/auth/linkedin`}
          className="inline-block px-4 py-2 bg-linkedin-600 hover:bg-linkedin-700 text-white rounded-lg font-semibold transition"
        >
          Connect via OAuth
        </a>
        <div className="text-sm mt-2 text-gray-500">{linkedinProfileUrl || 'No profile configured'}</div>
      </section>
    </div>
  );
}

export default function AdminSettingsPage() { return <ToastProvider><Suspense fallback={<div className="flex justify-center py-12"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-linkedin-600"></div></div>}><SettingsContent /></Suspense></ToastProvider>; }
