#!/usr/bin/env python3
"""
Model Discovery Agent — API-First Architecture
Tier 1: Official structured APIs (confidence 1.0)
Tier 2: Allowlisted official documentation pages (confidence 0.9)
Tier 3: Gemini reasoning fallback (confidence 0.7)
"""
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import argparse
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, TypedDict
from urllib.parse import urljoin, urlparse

import requests
import time
from dotenv import load_dotenv
from google.cloud import bigquery
from langgraph.graph import END, StateGraph


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_json(text: str, default: Any):
    if not text:
        return default

    # Remove markdown code blocks
    clean = text.replace("```json", "").replace("```", "").strip()

    # Try direct parse first
    try:
        return json.loads(clean)
    except Exception:
        pass

    # Try extracting JSON array or object
    try:
        m = re.search(r"(\[.*\])", clean, re.DOTALL)
        if m:
            return json.loads(m.group(1))
    except Exception:
        pass

    try:
        m = re.search(r"(\{.*\})", clean, re.DOTALL)
        if m:
            return json.loads(m.group(1))
    except Exception:
        pass

    # Last resort: look for array start and extract to end
    try:
        idx = clean.find("[")
        if idx >= 0:
            return json.loads(clean[idx:])
    except Exception:
        pass

    return default


def _source_domain(url: str) -> str:
    m = re.match(r"^https?://([^/]+)", (url or "").strip().lower())
    return m.group(1) if m else ""


def _is_official_domain(provider: str, source_url: str, official_domains_list: list[str]) -> bool:
    domain = _source_domain(source_url)
    if not domain:
        return False
    allowed = set()
    for d in official_domains_list:
        allowed.add(_source_domain(d if d.startswith("http") else f"https://{d}"))
    return domain in allowed


PROVIDER_CONFIG = {
    "openai": {
        "api_catalog": "https://api.openai.com/v1/models",
        "api_key_env": "OPENAI_API_KEY",
        "doc_urls": [
            "https://platform.openai.com/docs/models",
            "https://openai.com/api/pricing/",
        ],
        "official_domains": ["platform.openai.com", "openai.com", "api.openai.com"],
    },
    "google": {
        "api_catalog": None,
        "doc_urls": [
            "https://ai.google.dev/gemini-api/docs/models",
            "https://ai.google.dev/gemini-api/docs/pricing",
        ],
        "official_domains": ["ai.google.dev", "cloud.google.com"],
    },
    "anthropic": {
        "api_catalog": None,
        "doc_urls": [
            "https://docs.anthropic.com/en/docs/about-claude/models",
            "https://www.anthropic.com/pricing",
        ],
        "official_domains": ["docs.anthropic.com", "anthropic.com"],
    },
    "openrouter": {
        "api_catalog": "https://openrouter.ai/api/v1/models",
        "api_key_env": None,
        "doc_urls": [],
        "official_domains": ["openrouter.ai"],
    },
    "mistral": {
        "api_catalog": "https://api.mistral.ai/v1/models",
        "api_key_env": "MISTRAL_API_KEY",
        "doc_urls": ["https://docs.mistral.ai/getting-started/models/"],
        "official_domains": ["docs.mistral.ai", "api.mistral.ai"],
    },
    "cohere": {
        "api_catalog": "https://api.cohere.ai/v1/models",
        "api_key_env": "COHERE_API_KEY",
        "doc_urls": ["https://docs.cohere.com/v2/docs/models"],
        "official_domains": ["docs.cohere.com", "api.cohere.ai"],
    },
}

BLOCKED_PATH_TOKENS = ["/python/", "/java/", "/ruby/", "/go/", "/sdk/",
                       "/reference/", "/resources/", "/methods/"]


def provider_model_regex(provider: str) -> re.Pattern:
    p = provider.lower()
    if p == "openai":
        return re.compile(
            r"^(gpt-[a-z0-9.-]+|o[0-9][a-z0-9.-]*|text-embedding-[a-z0-9.-]+|"
            r"whisper-[a-z0-9.-]+|tts-[a-z0-9.-]+|dall-e-[a-z0-9.-]+|"
            r"babbage-[a-z0-9.-]+|davinci-[a-z0-9.-]+|chat-[a-z0-9.-]+|"
            r"chatgpt-[a-z0-9.-]+|omni-[a-z0-9.-]+|sora-[a-z0-9.-]+)$", re.I)
    if p == "google":
        return re.compile(r"^(models/)?(gemini|imagen|veo|gemma)-[a-z0-9.-]+$", re.I)
    if p == "anthropic":
        return re.compile(r"^claude-[a-z0-9.-]+$", re.I)
    return re.compile(r"^[a-z0-9][a-z0-9._/-]{1,80}$", re.I)


def _derive_family_version(provider: str, model_id: str) -> tuple[str, str]:
    m = model_id.strip().lower()
    p = provider.strip().lower()
    if p == "openai":
        if m.startswith("gpt-"):
            rest = m[4:]
            parts = rest.split("-")
            family = f"gpt-{parts[0]}" if parts else "gpt"
            return family, rest
        if re.match(r"^o[0-9]", m):
            return "o-series", m
        if m.startswith("text-embedding-"):
            return "text-embedding", m[len("text-embedding-"):]
        if m.startswith("whisper-"):
            return "whisper", m[len("whisper-"):]
        if m.startswith("tts-"):
            return "tts", m[len("tts-"):]
        if m.startswith("dall-e-"):
            return "dall-e", m[len("dall-e-"):]
    if p == "google":
        base = m[len("models/"):] if m.startswith("models/") else m
        for fam in ["gemini", "imagen", "veo", "gemma"]:
            if base.startswith(f"{fam}-"):
                return fam, base[len(fam) + 1:]
        return "google-model", base
    return p, m


class DiscoveryState(TypedDict, total=False):
    target_provider: str
    intelligence_model: str
    dry_run: bool
    force_official_only: bool
    allow_web_fallback: bool
    refresh_provider: bool
    skip_semantic_enrichment: bool
    started_at: str
    ended_at: str
    run_id: str

    structured_models: list[dict]
    docs_models: list[dict]
    fallback_models: list[dict]
    structured_source_used: bool
    docs_source_used: bool
    fallback_used: bool

    normalized_models: list[dict]
    approved_records: list[dict]
    rejected_records: list[dict]
    rejection_reasons: dict

    existing_models: list[dict]
    missing_models: list[dict]
    deprecated_candidates: list[dict]

    model_context: dict
    model_families: dict
    enriched_models: list[dict]

    semantic_enrichment_enabled: bool
    semantic_enrichment_completed: bool
    semantic_families_attempted: int
    semantic_families_completed: int
    semantic_enrichment_errors: list[str]

    inserts: list[dict]
    updates: list[dict]
    skips: list[dict]
    deprecated: list[dict]

    schema_migrations: list[str]
    errors: list[str]
    stopped: bool
    stop_reason: str
    export_candidates_only: bool
    candidate_json_path: str


def normalize_env() -> None:
    load_dotenv(".env.local", override=True)
    if os.getenv("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
    if os.getenv("SERAPI_KEY"):
        os.environ["SERPAPI_KEY"] = os.getenv("SERAPI_KEY", "")
    os.environ.pop("GOOGLE_GENAI_API_KEY", None)


normalize_env()

print("Using Gemini key:", "YES" if os.getenv("GOOGLE_API_KEY") else "NO")

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY (mapped from GEMINI_API_KEY)")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def _call_gemini_rest(prompt: str, timeout: int = 20) -> dict:
    """Call Gemini REST API directly (non-blocking, with timeout)."""
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 2000,
        },
    }

    try:
        resp = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        candidates = data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return {"success": True, "text": parts[0].get("text", "")}

        return {"success": False, "error": "No content in response"}

    except requests.Timeout:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}


print("Gemini REST API ready")


def node_provider_seed(state: DiscoveryState) -> DiscoveryState:
    provider = state.get("target_provider", "openai").lower()
    if provider not in PROVIDER_CONFIG:
        state["stopped"] = True
        state["stop_reason"] = f"Unknown provider: {provider}"
        return state
    if state.get("dry_run", False):
        print(f"Provider seed loaded: {provider}")
    return state


def _classify_openai_model(model_id: str) -> tuple[str, str, str]:
    """Classify OpenAI model into family, version, and release_stage."""
    mid = model_id.lower().strip()

    # o-series: o3, o4-mini, etc.
    if mid.startswith("o") and re.match(r"^o[0-9]", mid):
        family = "o-series"
        version = mid
        release_stage = "stable"
        return family, version, release_stage

    # GPT-5 variants
    if mid.startswith("gpt-5"):
        family = "gpt-5"
        version = mid[4:]
        if re.search(r"-\d{4}-\d{2}-\d{2}$", mid):
            release_stage = "versioned"
        else:
            release_stage = "stable"
        return family, version, release_stage

    # GPT-4o variants (check before GPT-4)
    if mid.startswith("gpt-4o"):
        family = "gpt-4o"
        version = mid[4:]
        if re.search(r"-\d{4}-\d{2}-\d{2}$", mid):
            release_stage = "versioned"
        else:
            release_stage = "stable"
        return family, version, release_stage

    # GPT-4.1, GPT-4 Turbo, GPT-4
    if mid.startswith("gpt-4"):
        family = "gpt-4"
        version = mid[4:]
        if re.search(r"-\d{4}-\d{2}-\d{2}$", mid):
            release_stage = "versioned"
        else:
            release_stage = "stable"
        return family, version, release_stage

    # GPT-3.5 variants
    if mid.startswith("gpt-3"):
        family = "gpt-3.5"
        version = mid[4:]
        if re.search(r"-\d{4}-\d{2}-\d{2}$", mid):
            release_stage = "versioned"
        else:
            release_stage = "stable"
        return family, version, release_stage

    # Text embedding
    if mid.startswith("text-embedding-"):
        family = "text-embedding"
        version = mid[len("text-embedding-"):]
        release_stage = "stable"
        return family, version, release_stage

    # Whisper audio
    if mid.startswith("whisper-"):
        family = "whisper"
        version = mid[len("whisper-"):]
        release_stage = "stable"
        return family, version, release_stage

    # TTS
    if mid.startswith("tts-"):
        family = "tts"
        version = mid[len("tts-"):]
        release_stage = "stable"
        return family, version, release_stage

    # GPT audio realtime
    if mid.startswith("gpt-audio"):
        family = "gpt-audio"
        version = mid[len("gpt-audio-"):]
        release_stage = "stable"
        return family, version, release_stage

    # GPT realtime
    if mid.startswith("gpt-realtime"):
        family = "gpt-realtime"
        version = mid[len("gpt-realtime-"):]
        release_stage = "stable"
        return family, version, release_stage

    # DALL-E
    if mid.startswith("dall-e-"):
        family = "dall-e"
        version = mid[len("dall-e-"):]
        release_stage = "stable"
        return family, version, release_stage

    # GPT Image generation models (gpt-image-1, gpt-image-2, etc.)
    if mid.startswith("gpt-image-"):
        family = "gpt-image"
        version = mid[len("gpt-image-"):]
        if re.search(r"-\d{4}-\d{2}-\d{2}$", mid):
            release_stage = "versioned"
        else:
            release_stage = "stable"
        return family, version, release_stage

    # Sora video (check before generic omni)
    if mid.startswith("sora-"):
        family = "video"
        version = mid[len("sora-"):]
        release_stage = "stable"
        return family, version, release_stage

    # Moderation models (check before generic omni)
    if mid.startswith("omni-moderation-"):
        family = "moderation"
        version = mid[len("omni-moderation-"):]
        if re.search(r"-\d{4}-\d{2}-\d{2}$", mid):
            release_stage = "versioned"
        else:
            release_stage = "stable"
        return family, version, release_stage

    # ChatGPT image models (check before generic chatgpt)
    if mid.startswith("chatgpt-image-"):
        family = "image"
        version = mid[len("chatgpt-image-"):]
        release_stage = "stable"
        return family, version, release_stage

    # ChatGPT models
    if mid.startswith("chatgpt-"):
        family = "chatgpt"
        version = mid[len("chatgpt-"):]
        release_stage = "stable"
        return family, version, release_stage

    # Chat models (chat-latest, etc.)
    if mid.startswith("chat-"):
        family = "chat"
        version = mid[len("chat-"):]
        release_stage = "stable"
        return family, version, release_stage

    # Computer use / agent tools
    if mid.startswith("computer-use-"):
        family = "agent-tools"
        version = mid[len("computer-use-"):]
        release_stage = "stable"
        return family, version, release_stage

    # Legacy Babbage models
    if mid.startswith("babbage-"):
        family = "legacy"
        version = mid[len("babbage-"):]
        release_stage = "stable"
        return family, version, release_stage

    # Legacy DaVinci models
    if mid.startswith("davinci-"):
        family = "legacy"
        version = mid[len("davinci-"):]
        release_stage = "stable"
        return family, version, release_stage

    # Omni models (general, catch-all for omni-* prefix)
    if mid.startswith("omni-"):
        family = "omni"
        version = mid[len("omni-"):]
        release_stage = "stable"
        return family, version, release_stage

    return "unknown", mid, "stable"


def node_official_structured_discovery(state: DiscoveryState) -> DiscoveryState:
    if state.get("stopped", False):
        return state

    provider = state.get("target_provider", "openai").lower()
    config = PROVIDER_CONFIG.get(provider, {})
    api_url = config.get("api_catalog")
    api_key_env = config.get("api_key_env")

    structured = []
    source_used = False
    error_reason = None

    if api_url:
        api_key = os.getenv(api_key_env) if api_key_env else None

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            resp = requests.get(api_url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if provider == "openai":
                for item in data.get("data", []):
                    mid = item.get("id", "").strip()
                    if mid:
                        structured.append({
                            "model_id": mid,
                            "source_url": api_url,
                            "source": "openai_api",
                            "confidence": 1.0,
                            "discovery_tier": 1,
                            "raw_item": item,
                        })
            elif provider in ["mistral", "cohere", "openrouter"]:
                for item in (data.get("data") if isinstance(data.get("data"), list) else [data]):
                    mid = item.get("id") if isinstance(item, dict) else str(item)
                    if mid:
                        mid = str(mid).strip()
                        structured.append({
                            "model_id": mid,
                            "source_url": api_url,
                            "source": f"{provider}_api",
                            "confidence": 1.0,
                            "discovery_tier": 1,
                        })

            source_used = len(structured) > 0
            print(f"Tier 1 ({provider} API): found {len(structured)} models")
        except Exception as e:
            error_reason = f"Tier 1 ({provider} API) failed: {str(e)[:100]}"
            print(error_reason)
    else:
        error_reason = f"Tier 1: no API catalog for {provider}"

    state["structured_models"] = structured
    state["structured_source_used"] = source_used
    if error_reason and state.get("dry_run"):
        print(error_reason)

    return state


def node_official_docs_discovery(state: DiscoveryState) -> DiscoveryState:
    if state.get("stopped", False):
        return state

    structured_used = state.get("structured_source_used", False)
    if structured_used:
        if state.get("dry_run"):
            print("Tier 1 succeeded. Skipping Tier 2 docs discovery.")
        state["docs_models"] = []
        state["docs_source_used"] = False
        return state

    provider = state.get("target_provider", "openai").lower()
    config = PROVIDER_CONFIG.get(provider, {})
    doc_urls = config.get("doc_urls", [])
    official_domains = config.get("official_domains", [])

    if not doc_urls:
        state["docs_models"] = []
        state["docs_source_used"] = False
        return state

    docs = []
    for url in doc_urls:
        if any(token in url for token in BLOCKED_PATH_TOKENS):
            if state.get("dry_run"):
                print(f"Blocking SDK wrapper URL: {url}")
            continue

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            text = resp.text[:10000]

            regex = provider_model_regex(provider)
            found = set()
            for match in regex.finditer(text):
                mid = match.group(0).strip()
                found.add(mid)

            for mid in found:
                docs.append({
                    "model_id": mid,
                    "source_url": url,
                    "source": "official_docs",
                    "confidence": 0.9,
                    "discovery_tier": 2,
                })

            print(f"Tier 2 ({url}): found {len(found)} model IDs")
        except Exception as e:
            print(f"Tier 2 ({url}) failed: {str(e)[:100]}")

    state["docs_models"] = docs
    state["docs_source_used"] = len(docs) > 0
    return state


def node_gemini_fallback(state: DiscoveryState) -> DiscoveryState:
    if state.get("stopped", False):
        return state

    structured_used = state.get("structured_source_used", False)
    docs_used = state.get("docs_source_used", False)
    allow_fallback = state.get("allow_web_fallback", False)

    if structured_used and not allow_fallback:
        if state.get("dry_run"):
            print("Tier 1 succeeded. Skipping Tier 3 Gemini fallback.")
        state["fallback_models"] = []
        state["fallback_used"] = False
        return state

    if (structured_used or docs_used) and not allow_fallback:
        state["fallback_models"] = []
        state["fallback_used"] = False
        return state

    provider = state.get("target_provider", "openai").lower()
    config = PROVIDER_CONFIG.get(provider, {})
    official_domains = config.get("official_domains", [])

    prompt = f"""Return only a JSON object with one field:
{{"official_urls": [...]}}

Find the top 5 official {provider.upper()} model catalog pages.
Must be from these domains: {', '.join(official_domains)}
Include only URLs with current model information.

Return ONLY the JSON object."""

    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        urls_data = _parse_json(resp.content, {})
        urls = urls_data.get("official_urls", [])
    except Exception as e:
        print(f"Tier 3 (Gemini) failed: {e}")
        state["fallback_models"] = []
        state["fallback_used"] = False
        return state

    fallback = []
    for url in urls:
        if not _is_official_domain(provider, url, official_domains):
            continue
        if any(token in url for token in BLOCKED_PATH_TOKENS):
            continue

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            text = resp.text[:10000]

            regex = provider_model_regex(provider)
            found = set()
            for match in regex.finditer(text):
                mid = match.group(0).strip().lower()
                found.add(mid)

            for mid in found:
                fallback.append({
                    "model_id": mid,
                    "source_url": url,
                    "source": "fallback_docs",
                    "confidence": 0.7,
                    "discovery_tier": 3,
                })
        except Exception:
            pass

    state["fallback_models"] = fallback
    state["fallback_used"] = len(fallback) > 0
    if state.get("dry_run"):
        print(f"Tier 3 (Gemini fallback): found {len(fallback)} models")

    return state


def node_model_normalization(state: DiscoveryState) -> DiscoveryState:
    if state.get("stopped", False):
        return state

    provider = state.get("target_provider", "openai").lower()
    regex = provider_model_regex(provider)

    all_models = (
        state.get("structured_models", []) +
        state.get("docs_models", []) +
        state.get("fallback_models", [])
    )

    dedup = {}
    for model in all_models:
        mid = model.get("model_id", "").strip()
        if not mid or not regex.match(mid.lower()):
            continue

        key = (provider, mid)
        if key not in dedup or model.get("confidence", 0) > dedup[key].get("confidence", 0):
            dedup[key] = model

    normalized = []
    unknown_models = []

    for model in dedup.values():
        mid = model.get("model_id", "").strip()
        mid_lower = mid.lower()

        if provider == "openai":
            fam, ver, release_stage = _classify_openai_model(mid)
            if fam == "unknown":
                unknown_models.append(mid)
        else:
            fam, ver = _derive_family_version(provider, mid_lower)
            release_stage = "stable"

        is_latest = mid.endswith("-latest") or mid.endswith("-latest-preview")

        rec = {
            "provider": provider,
            "model_id": mid,
            "display_name": mid,
            "family": fam,
            "version": ver,
            "release_stage": release_stage,
            "status": "current",
            "is_active": True,
            "is_latest": is_latest,
            "source_url": model.get("source_url", ""),
            "source_domain": _source_domain(model.get("source_url", "")),
            "confidence": model.get("confidence", 0.5),
            "discovery_tier": model.get("discovery_tier", 3),
            "discovered_at": _now(),
            "last_verified_at": _now(),
            "version_history": [
                {
                    "version": ver,
                    "release_date": None,
                    "status": "current",
                    "release_stage": release_stage,
                    "source_url": model.get("source_url", ""),
                    "discovered_at": _now(),
                    "verified_at": _now(),
                }
            ],
        }
        normalized.append(rec)

    state["normalized_models"] = normalized
    state["approved_records"] = normalized
    print(f"Normalized {len(normalized)} models")

    if unknown_models and state.get("dry_run", False):
        print(f"WARNING: {len(unknown_models)} unknown model families:")
        for mid in sorted(unknown_models):
            print(f"  - {mid}")

    if len(normalized) == 0:
        state["stopped"] = True
        state["stop_reason"] = "No models discovered from any tier"

    return state


def node_gather_official_metadata(state: DiscoveryState) -> DiscoveryState:
    """Gather official documentation context for models (non-blocking)."""
    if state.get("stopped", False):
        return state

    provider = state.get("target_provider", "openai").lower()

    if provider != "openai":
        state["model_context"] = {}
        return state

    official_urls = [
        "https://platform.openai.com/docs/models",
        "https://developers.openai.com/docs/guides/function-calling",
        "https://openai.com/api/pricing/",
    ]

    context_map = {}

    for url in official_urls:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 403:
                if state.get("dry_run"):
                    print(f"Metadata fetch ({url}): 403 Forbidden (skipping, non-critical)")
                continue
            resp.raise_for_status()
            text = resp.text[:15000]

            for model in state.get("approved_records", []):
                mid = model.get("model_id", "").lower()
                if mid not in context_map:
                    context_map[mid] = []

                if mid in text.lower() or model.get("family", "") in text.lower():
                    snippet_matches = re.finditer(f".{{0,150}}{re.escape(mid)}.{{0,150}}", text, re.I)
                    for match in snippet_matches:
                        context_map[mid].append(match.group(0).strip())
                        if len(context_map[mid]) >= 3:
                            break

        except requests.Timeout:
            if state.get("dry_run"):
                print(f"Metadata fetch ({url}): timeout (skipping, non-critical)")
        except Exception as e:
            if state.get("dry_run"):
                print(f"Metadata fetch ({url}): {str(e)[:80]} (skipping, non-critical)")

    state["model_context"] = context_map
    if state.get("dry_run"):
        print(f"Gathered context for {len(context_map)} models")

    return state


def node_batch_models_by_family(state: DiscoveryState) -> DiscoveryState:
    """Group models by family for efficient semantic enrichment."""
    if state.get("stopped", False):
        return state

    family_map = {}
    for model in state.get("approved_records", []):
        fam = model.get("family", "unknown")
        if fam not in family_map:
            family_map[fam] = []
        family_map[fam].append(model)

    state["model_families"] = family_map
    if state.get("dry_run"):
        print(f"Grouped {len(state.get('approved_records', []))} models into {len(family_map)} families")

    return state


def node_semantic_enrichment(state: DiscoveryState) -> DiscoveryState:
    """Enrich models with semantic metadata via Gemini REST API (non-blocking, with retry)."""
    if state.get("stopped", False):
        return state

    skip_enrichment = state.get("skip_semantic_enrichment", False)
    provider = state.get("target_provider", "openai").lower()

    if skip_enrichment or provider != "openai":
        # Still add default enrichment fields even when skipping enrichment
        approved = state.get("approved_records", [])
        for model in approved:
            model["model_purpose"] = model.get("model_purpose", f"{model.get('family', 'unknown')} model")
            model["recommended_for"] = model.get("recommended_for", ["general use"])
            model["avoid_for"] = model.get("avoid_for", [])
            model["user_persona"] = model.get("user_persona", ["developers"])
            model["selection_notes"] = model.get("selection_notes", "Default (enrichment skipped)")
            model["capabilities"] = model.get("capabilities", [])
            model["semantic_confidence"] = model.get("semantic_confidence", 0.3)
            model["official_context"] = model.get("official_context", "")

        state["enriched_models"] = approved
        state["semantic_enrichment_enabled"] = not skip_enrichment
        state["semantic_enrichment_completed"] = True
        return state

    state["semantic_enrichment_enabled"] = True
    state["semantic_families_attempted"] = 0
    state["semantic_families_completed"] = 0
    state["semantic_enrichment_errors"] = []

    model_families = state.get("model_families", {})
    model_context = state.get("model_context", {})
    enriched = []
    enrichment_start = time.time()
    enrichment_timeout = 300  # Max 5 minutes for all enrichment (17 families × ~10s each)
    family_timeout = 40  # Max 40 seconds per family (3 retries with backoff)

    for family_name, models in sorted(model_families.items()):
        # Check overall enrichment timeout
        elapsed = time.time() - enrichment_start
        if elapsed > enrichment_timeout:
            error_msg = f"Enrichment timeout exceeded ({enrichment_timeout}s after {elapsed:.1f}s). Skipping remaining families."
            state["semantic_enrichment_errors"].append(error_msg)
            if state.get("dry_run"):
                print(f"  ⚠ {error_msg}")
            break

        state["semantic_families_attempted"] += 1
        family_start_time = time.time()
        retry_count = 0

        family_context = []
        for model in models:
            mid = model.get("model_id", "").lower()
            ctx = model_context.get(mid, [])
            if ctx:
                family_context.extend(ctx[:2])

        if not family_context:
            family_context = [
                f"Family: {family_name}. Models: {', '.join([m.get('model_id', '') for m in models[:5]])}"
            ]

        context_text = "\n".join(family_context[:10])[:8000]

        model_list = ', '.join([m.get('model_id', '') for m in models])
        prompt = f"""You are a JSON generator. Generate a valid JSON array, no other text.

REQUIRED JSON FORMAT:
[{{"model_id": "model-name", "model_purpose": "text", "recommended_for": [], "avoid_for": [], "user_persona": [], "selection_notes": "text", "capabilities": [], "confidence": 0.8}}]

TASK: Create one object per model in this list: {model_list}

RULES:
1. Output ONLY valid JSON array, nothing else
2. Each object must have: model_id, model_purpose, recommended_for (array), avoid_for (array), user_persona (array), selection_notes (string), capabilities (array), confidence (0.0-1.0)
3. Use accurate model descriptions for the {family_name} family
4. confidence: 0.8 for accurate descriptions, 0.5-0.7 for uncertain
5. Do not wrap in markdown, backticks, or any other text

Valid example for family gpt-4o: [
{{"model_id": "gpt-4o", "model_purpose": "advanced general purpose chat and reasoning", "recommended_for": ["complex reasoning", "code generation", "analysis"], "avoid_for": ["real-time streaming", "latency-critical"], "user_persona": ["engineers", "researchers", "analysts"], "selection_notes": "Flagship model, best accuracy", "capabilities": ["vision", "function calling", "json mode"], "confidence": 0.9}}
]

Generate JSON array for the {family_name} models:"""

        result = None
        for attempt in range(3):
            # Check per-family timeout
            if time.time() - family_start_time > family_timeout:
                result = {"success": False, "error": f"Family timeout ({family_timeout}s)"}
                break

            if attempt > 0:
                backoff = [2, 5][attempt - 1]
                if state.get("dry_run"):
                    print(
                        f"  Semantic enrichment retry ({family_name}, attempt {attempt + 1}, backoff {backoff}s)"
                    )
                time.sleep(backoff)
                retry_count = attempt

            result = _call_gemini_rest(prompt, timeout=10)
            if result["success"]:
                break

        duration = time.time() - family_start_time

        if result and result["success"]:
            text_content = result.get("text", "").strip()

            # Debug: log raw response in dry_run mode
            if state.get("dry_run") and state.get("debug_semantic", False):
                print(f"    [DEBUG {family_name}] Raw response (first 200 chars): {text_content[:200]}")

            semantic_data = _parse_json(text_content, [])

            # Extract array from wrapped structure if needed
            if isinstance(semantic_data, dict):
                # Try common wrapper keys: models, data, results, items
                for key in ["models", "data", "results", "items"]:
                    if key in semantic_data and isinstance(semantic_data[key], list):
                        semantic_data = semantic_data[key]
                        break

                # If still a dict, try to extract first list value
                if isinstance(semantic_data, dict) and not isinstance(semantic_data, list):
                    # Last attempt: get first value that's a list
                    for v in semantic_data.values():
                        if isinstance(v, list):
                            semantic_data = v
                            break

            if isinstance(semantic_data, list) and len(semantic_data) > 0:
                enriched_count = 0
                for sem_item in semantic_data:
                    if not isinstance(sem_item, dict):
                        continue

                    mid = sem_item.get("model_id", "").lower()
                    matching_model = next(
                        (m for m in models if m.get("model_id", "").lower() == mid),
                        None,
                    )
                    if matching_model:
                        matching_model["model_purpose"] = sem_item.get(
                            "model_purpose", ""
                        )
                        matching_model["recommended_for"] = sem_item.get(
                            "recommended_for", []
                        )
                        matching_model["avoid_for"] = sem_item.get("avoid_for", [])
                        matching_model["user_persona"] = sem_item.get(
                            "user_persona", []
                        )
                        matching_model["selection_notes"] = sem_item.get(
                            "selection_notes", ""
                        )
                        matching_model["capabilities"] = sem_item.get(
                            "capabilities", []
                        )
                        matching_model["semantic_confidence"] = float(
                            sem_item.get("confidence", 0.5)
                        )
                        matching_model["official_context"] = context_text[:300]
                        enriched_count += 1

                if enriched_count > 0:
                    state["semantic_families_completed"] += 1
                    if state.get("dry_run"):
                        print(
                            f"  ✓ {family_name}: {len(models)} models ({duration:.1f}s, {enriched_count} enriched)"
                        )
                else:
                    error_msg = f"{family_name}: No matching models in response"
                    state["semantic_enrichment_errors"].append(error_msg)
                    if state.get("dry_run"):
                        print(f"  ⚠ {error_msg}")
            else:
                # Response parsed but empty or invalid structure - use fallback enrichment
                error_msg = f"{family_name}: Empty or invalid JSON array (got {type(semantic_data).__name__}), using fallback"
                state["semantic_enrichment_errors"].append(error_msg)
                if state.get("dry_run"):
                    print(f"  ⚠ {error_msg}")

                # Fallback: assign default semantic fields
                for model in models:
                    model["model_purpose"] = f"{family_name} model"
                    model["recommended_for"] = ["general use"]
                    model["avoid_for"] = []
                    model["user_persona"] = ["developers"]
                    model["selection_notes"] = "Default enrichment (Gemini response incomplete)"
                    model["capabilities"] = []
                    model["semantic_confidence"] = 0.3
                    model["official_context"] = context_text[:300]

        else:
            # API call failed - use fallback enrichment
            error_msg = f"{family_name}: {result.get('error', 'Unknown error') if result else 'No response'} (retries: {retry_count})"
            state["semantic_enrichment_errors"].append(error_msg)
            if state.get("dry_run"):
                print(f"  ⚠ {error_msg} ({duration:.1f}s)")

            # Fallback: assign default semantic fields
            for model in models:
                model["model_purpose"] = f"{family_name} model"
                model["recommended_for"] = ["general use"]
                model["avoid_for"] = []
                model["user_persona"] = ["developers"]
                model["selection_notes"] = f"Default enrichment (API error: {error_msg[:30]})"
                model["capabilities"] = []
                model["semantic_confidence"] = 0.3
                model["official_context"] = context_text[:300]

        enriched.extend(models)

    state["enriched_models"] = enriched
    state["semantic_enrichment_completed"] = True

    if state.get("dry_run"):
        print(
            f"Semantic enrichment: {state['semantic_families_completed']}/{state['semantic_families_attempted']} families"
        )
        if state["semantic_enrichment_errors"]:
            print(f"  Warnings: {len(state['semantic_enrichment_errors'])}")

    return state


def node_version_history_merge(state: DiscoveryState) -> DiscoveryState:
    if state.get("stopped", False):
        return state

    existing_by_key = {(r["provider"], r["model_id"]): r for r in state.get("existing_models", [])}
    records = state.get("enriched_models", state.get("approved_records", []))

    for rec in records:
        key = (rec["provider"], rec["model_id"])
        old = existing_by_key.get(key)

        if old:
            rec["first_seen_at"] = old.get("first_seen_at", _now())

            old_vh = old.get("version_history", []) or []
            new_vh = rec.get("version_history", [])

            merged_vh = list(old_vh)
            for new_entry in new_vh:
                if not any(h.get("version") == new_entry.get("version") for h in old_vh):
                    merged_vh.append(new_entry)

            rec["version_history"] = merged_vh
        else:
            rec["first_seen_at"] = _now()

    return state


def node_safe_deprecation(state: DiscoveryState) -> DiscoveryState:
    if state.get("stopped", False):
        return state

    provider = state.get("target_provider", "openai").lower()
    existing = {(r["provider"], r["model_id"]): r for r in state.get("existing_models", [])}
    records = state.get("enriched_models", state.get("approved_records", []))
    approved_keys = {(r["provider"], r["model_id"]) for r in records}

    missing = []
    for key, old_rec in existing.items():
        if old_rec.get("provider") != provider:
            continue

        if key not in approved_keys:
            missing_count = old_rec.get("missing_scan_count", 0) + 1

            if missing_count >= 3:
                old_rec["model_status"] = "deprecated"
                old_rec["is_active"] = False
                old_rec["missing_scan_count"] = missing_count
                state["deprecated"] = state.get("deprecated", []) + [old_rec]
            else:
                old_rec["missing_scan_count"] = missing_count
                missing.append(old_rec)

    state["missing_models"] = missing

    if state.get("dry_run"):
        print(f"Safe deprecation: {len(missing)} candidates (< 3 misses), {len(state.get('deprecated', []))} deprecated (>= 3 misses)")

    return state


def node_fetch_existing(state: DiscoveryState) -> DiscoveryState:
    if state.get("stopped", False):
        state["existing_models"] = []
        return state

    project = os.getenv("GOOGLE_CLOUD_PROJECT", "ctoteam")
    client = bigquery.Client(project=project)

    try:
        query = f"""
        SELECT * FROM `{project}.linkedin_studio.ai_models`
        """
        rows = client.query(query).result()
        state["existing_models"] = [dict(r) for r in rows]
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"BigQuery fetch: {e}"]
        state["existing_models"] = []

    return state


def node_schema_check(state: DiscoveryState) -> DiscoveryState:
    if state.get("dry_run", False) or state.get("stopped", False) or state.get("export_candidates_only", False):
        return state

    project = os.getenv("GOOGLE_CLOUD_PROJECT", "ctoteam")
    client = bigquery.Client(project=project)
    table_id = f"{project}.linkedin_studio.ai_models"

    required_cols = {
        "missing_scan_count": "INT64",
        "last_seen_at": "TIMESTAMP",
        "first_seen_at": "TIMESTAMP",
        "discovery_tier": "INT64",
        "model_purpose": "STRING",
        "recommended_for": "ARRAY<STRING>",
        "avoid_for": "ARRAY<STRING>",
        "user_persona": "ARRAY<STRING>",
        "selection_notes": "STRING",
        "capabilities": "ARRAY<STRING>",
        "semantic_confidence": "FLOAT64",
        "official_context": "STRING",
    }

    try:
        table = client.get_table(table_id)
        existing_cols = {field.name: field.field_type for field in table.schema}
    except Exception as e:
        # Table doesn't exist - create it with required schema
        if "Not found" in str(e) or "was not found" in str(e):
            print(f"Table not found. Creating {table_id}...")
            try:
                # Build schema from required columns + core fields
                schema = [
                    bigquery.SchemaField("provider", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("model_id", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("display_name", "STRING"),
                    bigquery.SchemaField("family", "STRING"),
                    bigquery.SchemaField("version", "STRING"),
                    bigquery.SchemaField("release_stage", "STRING"),
                    bigquery.SchemaField("is_active", "BOOLEAN"),
                    bigquery.SchemaField("source_url", "STRING"),
                    bigquery.SchemaField("source_domain", "STRING"),
                    bigquery.SchemaField("discovered_at", "TIMESTAMP"),
                    bigquery.SchemaField("last_verified_at", "TIMESTAMP"),
                ]
                # Add required enrichment columns
                for col_name, col_type in required_cols.items():
                    if col_type.startswith("ARRAY"):
                        mode = "REPEATED"
                        base_type = col_type.replace("ARRAY<", "").replace(">", "")
                    else:
                        mode = "NULLABLE"
                        base_type = col_type
                    schema.append(bigquery.SchemaField(col_name, base_type, mode=mode))

                table = bigquery.Table(table_id, schema=schema)
                table = client.create_table(table)
                print(f"✓ Created table {table_id} with {len(schema)} columns")
                existing_cols = {field.name: field.field_type for field in table.schema}
            except Exception as create_err:
                state["errors"] = state.get("errors", []) + [f"BigQuery table creation failed: {create_err}"]
                return state
        else:
            state["errors"] = state.get("errors", []) + [f"BigQuery schema check failed: {e}"]
            return state

    migrations = []
    for col_name, col_type in required_cols.items():
        if col_name not in existing_cols:
            try:
                alter_sql = f"ALTER TABLE `{table_id}` ADD COLUMN {col_name} {col_type}"
                client.query(alter_sql).result()
                migrations.append(f"Added {col_name} {col_type}")
                print(f"Schema: Added column {col_name}")
            except Exception as e:
                msg = f"Failed to add column {col_name}: {e}"
                state["errors"] = state.get("errors", []) + [msg]
                print(msg)

    state["schema_migrations"] = migrations
    return state


def node_diff(state: DiscoveryState) -> DiscoveryState:
    existing = {(r["provider"], r["model_id"]): r for r in state.get("existing_models", [])}
    records = state.get("enriched_models", state.get("approved_records", []))
    inserts, updates, skips = [], [], []

    for rec in records:
        k = (rec["provider"], rec["model_id"])
        old = existing.get(k)

        if not old:
            inserts.append(rec)
        elif any(old.get(f) != rec.get(f) for f in [
            "display_name", "source_url", "source_domain", "family", "version",
            "release_stage", "confidence", "discovery_tier", "model_purpose",
            "semantic_confidence"
        ]):
            updates.append(rec)
        else:
            skips.append(rec)

    state["inserts"] = inserts
    state["updates"] = updates
    state["skips"] = skips

    if state.get("dry_run"):
        print(f"Diff: inserts={len(inserts)}, updates={len(updates)}, skips={len(skips)}")

    return state


def check_and_repair_duplicates(client, table_id: str, repair: bool = False) -> dict:
    """Check for duplicate rows and optionally repair them.

    Returns:
    {
        "has_duplicates": bool,
        "total_rows": int,
        "unique_models": int,
        "duplicates": {provider:model_id -> count, ...}
        "repaired": bool
    }
    """
    # Check for duplicates
    check_sql = f"""
    SELECT provider, model_id, COUNT(*) as cnt
    FROM `{table_id}`
    GROUP BY provider, model_id
    HAVING COUNT(*) > 1
    ORDER BY cnt DESC
    """

    try:
        result = client.query(check_sql).result()
        duplicates = {f"{row.provider}:{row.model_id}": row.cnt for row in result}
    except Exception as e:
        return {"has_duplicates": False, "error": str(e), "duplicates": {}, "repaired": False, "total_rows": 0, "unique_models": 0}

    # Get total stats
    stats_sql = f"""
    SELECT COUNT(*) as total, COUNT(DISTINCT CONCAT(provider, ':', model_id)) as unique_models
    FROM `{table_id}`
    """
    stats_list = list(client.query(stats_sql).result())
    total_rows = stats_list[0].total
    unique_models = stats_list[0].unique_models

    if not duplicates:
        return {
            "has_duplicates": False,
            "total_rows": total_rows,
            "unique_models": unique_models,
            "duplicates": {},
            "repaired": False
        }

    # Has duplicates
    print(f"\n⚠ WARNING: Found {len(duplicates)} model(s) with duplicates!")
    print(f"  Total rows: {total_rows}")
    print(f"  Unique models: {unique_models}")
    print(f"  Duplicates: {duplicates}")

    if not repair:
        print("\nTo repair, run: python agents/model_discovery_langgraph_agent.py --repair-duplicates")
        return {
            "has_duplicates": True,
            "total_rows": total_rows,
            "unique_models": unique_models,
            "duplicates": duplicates,
            "repaired": False
        }

    # Repair: keep only the latest row per provider/model_id
    print("\n🔧 Repairing duplicates (keeping latest per provider/model_id)...")
    repair_sql = f"""
    DELETE FROM `{table_id}`
    WHERE CONCAT(provider, ':', model_id, ':', CAST(last_verified_at AS STRING)) NOT IN (
        SELECT CONCAT(provider, ':', model_id, ':', CAST(MAX(last_verified_at) AS STRING))
        FROM `{table_id}`
        GROUP BY provider, model_id
    )
    """

    try:
        client.query(repair_sql).result()
        print("✓ Duplicates removed")

        # Verify repair
        result_list = list(client.query(stats_sql).result())
        new_total = result_list[0].total
        new_unique = result_list[0].unique_models
        print(f"✓ After repair: {new_total} total rows, {new_unique} unique models")

        return {
            "has_duplicates": False,
            "total_rows": new_total,
            "unique_models": new_unique,
            "duplicates": {},
            "repaired": True
        }
    except Exception as e:
        print(f"✗ Repair failed: {e}")
        return {
            "has_duplicates": True,
            "total_rows": total_rows,
            "unique_models": unique_models,
            "duplicates": duplicates,
            "repaired": False,
            "error": str(e)
        }


def node_upsert(state: DiscoveryState) -> DiscoveryState:
    if state.get("dry_run", False) or state.get("stopped", False) or state.get("export_candidates_only", False):
        return state

    project = os.getenv("GOOGLE_CLOUD_PROJECT", "ctoteam")
    client = bigquery.Client(project=project)
    table_id = f"{project}.linkedin_studio.ai_models"

    to_write = state.get("inserts", []) + state.get("updates", [])

    if not to_write:
        return state

    # Check for existing duplicates
    repair_duplicates = state.get("repair_duplicates", False)
    dup_check = check_and_repair_duplicates(client, table_id, repair=repair_duplicates)

    if dup_check.get("has_duplicates") and not repair_duplicates:
        state["stopped"] = True
        state["stop_reason"] = "Duplicates exist in BigQuery. Run with --repair-duplicates to fix"
        state["errors"] = state.get("errors", []) + [dup_check.get("stop_reason", "Duplicates found")]
        return state

    # Fields that are safe to include (exist in BigQuery schema)
    core_fields = ["model_id", "provider", "display_name"]
    semantic_fields = ["model_purpose", "recommended_for", "avoid_for", "user_persona",
                      "selection_notes", "capabilities", "semantic_confidence", "official_context"]
    temporal_fields = ["missing_scan_count", "last_seen_at", "first_seen_at", "discovery_tier"]

    rows_to_insert = []
    for rec in to_write:
        row = {}

        # Add core fields
        for field in core_fields:
            if field in rec:
                row[field] = rec[field]

        # Add semantic fields
        for field in semantic_fields:
            row[field] = rec.get(field, "" if field.endswith("_notes") or field.endswith("_context") else ([] if field.endswith("_for") or field.endswith("persona") or field == "capabilities" else 0.0))

        # Add temporal fields
        row["missing_scan_count"] = rec.get("missing_scan_count", 0)
        row["last_seen_at"] = _now()

        # Convert datetime to ISO string if needed
        first_seen = rec.get("first_seen_at", _now())
        if hasattr(first_seen, 'isoformat'):
            first_seen = first_seen.isoformat()
        row["first_seen_at"] = first_seen

        row["discovery_tier"] = rec.get("discovery_tier", 1)

        rows_to_insert.append(row)

    # Deduplicate source rows (keep latest per provider/model_id)
    dedup_map = {}
    for row in rows_to_insert:
        key = (row.get("provider"), row.get("model_id"))
        # Keep row with latest last_verified_at
        if key not in dedup_map:
            dedup_map[key] = row
        else:
            existing = dedup_map[key]
            current_time = row.get("last_verified_at", "")
            existing_time = existing.get("last_verified_at", "")
            # Keep the one with later timestamp (string comparison works for ISO format)
            if current_time > existing_time:
                dedup_map[key] = row

    deduped_rows = list(dedup_map.values())

    try:
        errors = client.insert_rows_json(table_id, deduped_rows)
        if errors:
            msg = f"BigQuery insert errors: {errors}"
            state["errors"] = state.get("errors", []) + [msg]
            print(msg)
        else:
            print(f"Upserted {len(deduped_rows)} models to BigQuery")
            print(f"  Inserts: {len(state.get('inserts', []))}")
            print(f"  Updates: {len(state.get('updates', []))}")

            # Verify final state
            verify_sql = f"""
            SELECT COUNT(*) as total, COUNT(DISTINCT CONCAT(provider, ':', model_id)) as unique_models
            FROM `{table_id}`
            WHERE provider = '{state.get('target_provider', 'openai')}'
            """
            result = client.query(verify_sql).result()
            stats = list(result)[0]
            print(f"  BigQuery after upsert: {stats.total} total rows, {stats.unique_models} unique models")

    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"BigQuery upsert failed: {e}"]

    return state


def node_export_candidates(state: DiscoveryState) -> DiscoveryState:
    provider = state.get("target_provider", "openai").lower()
    run_id = state.get("run_id", "")
    candidate_path = f"agents/model_discovery_candidates_{provider}.json"

    enriched_models = state.get("enriched_models", state.get("approved_records", []))

    payload = {
        "run_id": run_id,
        "started_at": state.get("started_at", ""),
        "target_provider": provider,
        "structured_source_used": state.get("structured_source_used", False),
        "docs_source_used": state.get("docs_source_used", False),
        "fallback_used": state.get("fallback_used", False),
        "semantic_enrichment": len(
            [m for m in enriched_models if m.get("model_purpose")]
        ),
        "normalized_models": state.get("normalized_models", []),
        "enriched_models": enriched_models,
        "rejected_records": state.get("rejected_records", []),
        "missing_models": state.get("missing_models", []),
        "deprecated_candidates": state.get("deprecated_candidates", []),
        "planned_bigquery_actions": {
            "inserts": state.get("inserts", []),
            "updates": state.get("updates", []),
            "skips": state.get("skips", []),
            "deprecated": state.get("deprecated", []),
        },
        "dry_run": state.get("dry_run", False),
    }

    def _convert_datetime(obj):
        """Convert datetime objects to ISO strings for JSON serialization."""
        if isinstance(obj, dict):
            return {k: _convert_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_convert_datetime(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # datetime, date, time objects
            return obj.isoformat()
        return obj

    payload = _convert_datetime(payload)

    with open(candidate_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    state["candidate_json_path"] = candidate_path
    print(f"Candidate JSON written to {candidate_path}")

    if state.get("export_candidates_only", False):
        state["stopped"] = True
        state["stop_reason"] = "Export candidates only mode"
    elif len(enriched_models) == 0:
        state["stopped"] = True
        state["stop_reason"] = "No approved records to write"

    return state


def node_audit(state: DiscoveryState) -> DiscoveryState:
    state["ended_at"] = _now()

    audit = {
        "started_at": state.get("started_at", ""),
        "ended_at": state.get("ended_at", ""),
        "target_provider": state.get("target_provider", ""),
        "intelligence_model": "gemini-2.5-flash",
        "run_id": state.get("run_id", ""),

        "structured_source_used": state.get("structured_source_used", False),
        "docs_source_used": state.get("docs_source_used", False),
        "fallback_used": state.get("fallback_used", False),

        "structured_models_count": len(state.get("structured_models", [])),
        "docs_models_count": len(state.get("docs_models", [])),
        "fallback_models_count": len(state.get("fallback_models", [])),
        "normalized_count": len(state.get("normalized_models", [])),

        "semantic_enrichment_enabled": state.get("semantic_enrichment_enabled", False),
        "semantic_enrichment_completed": state.get("semantic_enrichment_completed", False),
        "semantic_families_attempted": state.get("semantic_families_attempted", 0),
        "semantic_families_completed": state.get("semantic_families_completed", 0),
        "semantic_enrichment_errors": state.get("semantic_enrichment_errors", []),

        "approved_records_count": len(state.get("approved_records", [])),
        "enriched_models_count": len(state.get("enriched_models", [])),
        "missing_models_count": len(state.get("missing_models", [])),
        "deprecated_candidates_count": len(state.get("deprecated_candidates", [])),

        "inserts_count": len(state.get("inserts", [])),
        "updates_count": len(state.get("updates", [])),
        "skips_count": len(state.get("skips", [])),
        "deprecated_count": len(state.get("deprecated", [])),

        "schema_migrations": state.get("schema_migrations", []),
        "errors": state.get("errors", []),
        "stopped": state.get("stopped", False),
        "stop_reason": state.get("stop_reason", ""),
        "dry_run": state.get("dry_run", False),
    }

    audit_path = "agents/model_discovery_audit.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)
    print(f"Audit written to {audit_path}")

    return state


def build_graph():
    g = StateGraph(DiscoveryState)
    g.add_node("seed", node_provider_seed)
    g.add_node("structured", node_official_structured_discovery)
    g.add_node("docs", node_official_docs_discovery)
    g.add_node("fallback", node_gemini_fallback)
    g.add_node("normalize", node_model_normalization)
    g.add_node("gather_metadata", node_gather_official_metadata)
    g.add_node("batch_families", node_batch_models_by_family)
    g.add_node("semantic_enrich", node_semantic_enrichment)
    g.add_node("fetch_existing", node_fetch_existing)
    g.add_node("version_history", node_version_history_merge)
    g.add_node("safe_deprecation", node_safe_deprecation)
    g.add_node("schema_check", node_schema_check)
    g.add_node("diff", node_diff)
    g.add_node("export", node_export_candidates)
    g.add_node("upsert", node_upsert)
    g.add_node("audit", node_audit)

    g.set_entry_point("seed")
    g.add_edge("seed", "structured")
    g.add_edge("structured", "docs")
    g.add_edge("docs", "fallback")
    g.add_edge("fallback", "normalize")
    g.add_edge("normalize", "gather_metadata")
    g.add_edge("gather_metadata", "batch_families")
    g.add_edge("batch_families", "semantic_enrich")
    g.add_edge("semantic_enrich", "schema_check")
    g.add_edge("schema_check", "fetch_existing")
    g.add_edge("fetch_existing", "version_history")
    g.add_edge("version_history", "safe_deprecation")
    g.add_edge("safe_deprecation", "diff")
    g.add_edge("diff", "export")
    g.add_edge("export", "upsert")
    g.add_edge("upsert", "audit")
    g.add_edge("audit", END)

    return g.compile()


def run(target_provider: str, dry_run: bool, export_candidates_only: bool,
        force_official_only: bool, allow_web_fallback: bool, refresh_provider: bool,
        skip_semantic_enrichment: bool, repair_duplicates: bool = False):

    print("=" * 60)
    print("MODEL DISCOVERY — API-FIRST ARCHITECTURE")
    print("=" * 60)
    print(f"Target provider: {target_provider}")
    print(f"Intelligence model: gemini-2.5-flash")
    print(f"Tier 1: Official structured APIs (confidence 1.0)")
    print(f"Tier 2: Allowlisted documentation pages (confidence 0.9)")
    print(f"Tier 3: Gemini reasoning fallback (confidence 0.7)")
    print("=" * 60)

    app = build_graph()
    state: DiscoveryState = {
        "target_provider": target_provider.lower(),
        "intelligence_model": "gemini-2.5-flash",
        "dry_run": dry_run,
        "force_official_only": force_official_only,
        "allow_web_fallback": allow_web_fallback,
        "refresh_provider": refresh_provider,
        "skip_semantic_enrichment": skip_semantic_enrichment,
        "repair_duplicates": repair_duplicates,
        "started_at": _now(),
        "errors": [],
        "export_candidates_only": export_candidates_only,
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"),
        "stopped": False,
        "stop_reason": "",
        "structured_models": [],
        "docs_models": [],
        "fallback_models": [],
        "normalized_models": [],
        "approved_records": [],
        "rejected_records": [],
        "model_context": {},
        "model_families": {},
        "enriched_models": [],
        "semantic_enrichment_enabled": False,
        "semantic_enrichment_completed": False,
        "semantic_families_attempted": 0,
        "semantic_families_completed": 0,
        "semantic_enrichment_errors": [],
        "inserts": [],
        "updates": [],
        "skips": [],
        "deprecated": [],
        "missing_models": [],
        "deprecated_candidates": [],
    }

    out = app.invoke(state)

    enriched_models = out.get("enriched_models", out.get("approved_records", []))
    enriched_count = sum(1 for m in enriched_models if m.get("model_purpose"))

    print("\n" + "=" * 60)
    print("DISCOVERY RESULTS")
    print("=" * 60)
    print(f"Tier 1 (structured API): {len(out.get('structured_models', []))} models")
    print(f"Tier 2 (official docs): {len(out.get('docs_models', []))} models")
    print(f"Tier 3 (Gemini fallback): {len(out.get('fallback_models', []))} models")
    print(f"Normalized: {len(out.get('normalized_models', []))} models")

    if out.get("semantic_enrichment_enabled"):
        print(
            f"Semantic enrichment: {out.get('semantic_families_completed', 0)}/{out.get('semantic_families_attempted', 0)} families, "
            f"{enriched_count}/{len(enriched_models)} models enriched"
        )
        if out.get("semantic_enrichment_errors"):
            print(f"  Warnings: {len(out.get('semantic_enrichment_errors', []))}")
    else:
        print("Semantic enrichment: skipped")

    print(f"Missing (pending deprecation): {len(out.get('missing_models', []))}")
    print(f"Deprecated (>= 3 misses): {len(out.get('deprecated', []))}")
    print(f"BigQuery: inserts={len(out.get('inserts', []))}, updates={len(out.get('updates', []))}, skips={len(out.get('skips', []))}")
    print(f"Schema migrations: {len(out.get('schema_migrations', []))}")
    print(f"Errors: {len(out.get('errors', []))}")
    if out.get('errors'):
        for err in out.get('errors', [])[:5]:
            print(f"  - {err[:100]}")
    print(f"Stopped: {out.get('stopped', False)}")
    if out.get("stop_reason"):
        print(f"Stop reason: {out.get('stop_reason')}")
    print(f"Candidates file: {out.get('candidate_json_path', '')}")
    print(f"Audit file: agents/model_discovery_audit.json")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Model discovery agent with API-first architecture"
    )
    parser.add_argument(
        "--target-provider",
        choices=["openai", "google", "anthropic", "openrouter", "mistral", "cohere"],
        default="openai",
        help="Provider whose models to discover"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without writing to BigQuery"
    )
    parser.add_argument(
        "--export-candidates-only",
        action="store_true",
        help="Write candidate JSON only, skip BigQuery"
    )
    parser.add_argument(
        "--force-official-only",
        action="store_true",
        help="Fail if Tier 1 unavailable, skip Tier 2+3"
    )
    parser.add_argument(
        "--allow-web-fallback",
        action="store_true",
        help="Enable Tier 3 Gemini reasoning fallback even if Tier 1+2 succeed"
    )
    parser.add_argument(
        "--refresh-provider",
        action="store_true",
        help="Force re-discovery regardless of last scan time"
    )
    parser.add_argument(
        "--skip-semantic-enrichment",
        action="store_true",
        help="Skip semantic enrichment; use null/empty semantic fields"
    )
    parser.add_argument(
        "--repair-duplicates",
        action="store_true",
        help="Remove duplicate rows (keeping latest per provider/model_id); only if duplicates found"
    )

    args = parser.parse_args()

    run(
        target_provider=args.target_provider,
        dry_run=args.dry_run,
        export_candidates_only=args.export_candidates_only,
        force_official_only=args.force_official_only,
        allow_web_fallback=args.allow_web_fallback,
        refresh_provider=args.refresh_provider,
        skip_semantic_enrichment=args.skip_semantic_enrichment,
        repair_duplicates=args.repair_duplicates,
    )
