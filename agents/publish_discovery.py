#!/usr/bin/env python3
"""
publish_discovery.py
Reads model discovery JSON → generates charts → posts to LinkedIn + Medium
Usage: python agents/publish_discovery.py agents/model_discovery_candidates_openai.json
"""

import json
import os
import sys
import requests
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Load .env file
load_dotenv("backend/.env.local")
load_dotenv("backend/.env")

# ── Config from env ───────────────────────────────────────────────────────────
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINKEDIN_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_AUTHOR_URN")
MEDIUM_TOKEN = os.getenv("MEDIUM_TOKEN")
MEDIUM_USER_ID = os.getenv("MEDIUM_USER_ID")
OUTPUT_DIR = "reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Step 0: Determine model use case and recommendation ────────────────────────
def get_model_usecase_and_recommendation(model):
    """
    Determine the primary use case and recommendation tier for a model.
    Returns: (use_case: str, recommendation: str, color: str)
    """
    model_id = model.get("model_id", "").lower()
    family = model.get("family", "").lower()
    is_latest = model.get("is_latest", False)
    is_active = model.get("is_active", False)
    stage = model.get("release_stage", "").lower()

    # Determine base recommendation tier
    flagship_families = ["gpt-5", "gpt-4o", "o-series", "gpt-4", "gpt-3.5"]
    is_flagship = any(f in family for f in flagship_families)

    # Use case & recommendation mapping
    if any(x in model_id for x in ["gpt-5", "o4", "o1", "o3"]):
        use_case = "Complex reasoning"
        rec = "[RECOMMENDED]" if (is_latest and is_flagship) else "[GOOD]" if is_active else "[DEPRECATED]"
        color = "#1e40af" if (is_latest and is_flagship) else "#3b82f6" if is_active else "#6b7280"

    elif "gpt-4o" in model_id:
        use_case = "Versatile multimodal"
        rec = "[RECOMMENDED]" if is_latest else "[GOOD]"
        color = "#059669" if is_latest else "#10b981"

    elif any(x in model_id for x in ["gpt-3.5", "gpt-4-turbo"]):
        use_case = "Fast & capable"
        rec = "[RECOMMENDED]" if is_latest else "[GOOD]"
        color = "#10b981" if is_latest else "#84cc16"

    elif any(x in model_id for x in ["gpt-4", "gpt-realtime", "gpt-audio"]):
        use_case = "Advanced models"
        rec = "[RECOMMENDED]" if (is_latest and stage == "stable") else "[GOOD]" if is_active else "[NICHE]"
        color = "#1e40af" if (is_latest and stage == "stable") else "#3b82f6" if is_active else "#8b5cf6"

    elif "embedding" in family:
        use_case = "Semantic search"
        rec = "[RECOMMENDED]" if is_latest else "[GOOD]"
        color = "#7c3aed" if is_latest else "#a78bfa"

    elif "dall-e" in model_id or "image" in family:
        use_case = "Image generation"
        rec = "[RECOMMENDED]" if is_latest else "[GOOD]"
        color = "#ec4899" if is_latest else "#f472b6"

    elif "whisper" in model_id:
        use_case = "Speech-to-text"
        rec = "[RECOMMENDED]" if is_latest else "[GOOD]"
        color = "#f59e0b" if is_latest else "#fbbf24"

    elif "tts" in model_id:
        use_case = "Text-to-speech"
        rec = "[RECOMMENDED]" if is_latest else "[GOOD]"
        color = "#f97316" if is_latest else "#fb923c"

    elif "video" in family or "sora" in model_id:
        use_case = "Video generation"
        rec = "[NICHE]" if is_active else "[DEPRECATED]"
        color = "#8b5cf6" if is_active else "#6b7280"

    elif "moderation" in family:
        use_case = "Content moderation"
        rec = "[GOOD]"
        color = "#06b6d4"

    elif not is_active or "legacy" in family or "babbage" in model_id:
        use_case = "Legacy/Deprecated"
        rec = "[DEPRECATED]"
        color = "#6b7280"

    else:
        use_case = "Specialized"
        rec = "[NICHE]"
        color = "#8b5cf6"

    return use_case, rec, color


# ── Step 1: Parse JSON ────────────────────────────────────────────────────────
def parse_json(path):
    """Parse discovery JSON and compute statistics."""
    with open(path) as f:
        data = json.load(f)

    models = data.get("normalized_models", [])
    provider = data.get("target_provider", "openai").upper()
    run_id = data.get("run_id", datetime.now().isoformat())
    run_date = run_id[:10] if len(run_id) >= 10 else datetime.now().strftime("%Y-%m-%d")

    # Add use case and recommendation info
    for m in models:
        use_case, rec, color = get_model_usecase_and_recommendation(m)
        m["use_case"] = use_case
        m["recommendation"] = rec
        m["rec_color"] = color
        # For backward compat, use recommendation tier as numeric score
        rec_scores = {"⭐ RECOMMENDED": 1.0, "✓ GOOD": 0.75, "⚠ NICHE": 0.5, "⚠ DEPRECATED": 0.2}
        m["enriched_confidence"] = rec_scores.get(rec, 0.5)

    families = defaultdict(list)
    for m in models:
        families[m["family"]].append(m)

    latest_per_family = {}
    for fam, mlist in families.items():
        latest = [m for m in mlist if m.get("is_latest")]
        latest_per_family[fam] = (
            latest[0]
            if latest
            else sorted(mlist, key=lambda x: x.get("discovered_at", ""), reverse=True)[0]
        )

    stage_counts = defaultdict(int)
    conf_buckets = {"high": [], "medium": [], "low": []}
    for m in models:
        stage_counts[m.get("release_stage", "unknown")] += 1
        c = m.get("enriched_confidence", 0)
        if c >= 0.8:
            conf_buckets["high"].append(m)
        elif c >= 0.5:
            conf_buckets["medium"].append(m)
        else:
            conf_buckets["low"].append(m)

    # Purpose classification
    purpose_map = {
        "text-generation": ["gpt", "chat", "o-series", "legacy"],
        "image": ["dall-e", "gpt-image", "image"],
        "video": ["sora", "video", "veo"],
        "audio": ["tts", "whisper", "gpt-audio", "gpt-realtime"],
        "embedding": ["text-embedding", "embedding"],
        "moderation": ["moderation"],
    }
    purpose_counts = defaultdict(int)
    for m in models:
        fam = m.get("family", "")
        matched = False
        for purpose, keywords in purpose_map.items():
            if any(k in fam.lower() for k in keywords):
                purpose_counts[purpose] += 1
                matched = True
                break
        if not matched:
            purpose_counts["other"] += 1

    return {
        "provider": provider,
        "run_id": run_id,
        "run_date": run_date,
        "total": len(models),
        "families": dict(families),
        "family_count": len(families),
        "latest_per_family": latest_per_family,
        "stage_counts": dict(stage_counts),
        "conf_buckets": conf_buckets,
        "purpose_counts": dict(purpose_counts),
        "all_models": models,
    }


# ── Step 2: Generate Model Selection Table ─────────────────────────────────────
def generate_charts(stats):
    """Generate a developer-friendly model selection table."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    provider = stats["provider"]
    BG = "#ffffff"
    CARD = "#f8fafc"
    GRID = "#e2e8f0"
    TEXT = "#475569"
    HEAD = "#0f172a"

    # Group models by use case
    use_case_groups = {}
    for fam, mods in stats["families"].items():
        for m in mods:
            uc = m.get("use_case", "Other")
            if uc not in use_case_groups:
                use_case_groups[uc] = []
            use_case_groups[uc].append(m)

    # Create table visualization
    fig = plt.figure(figsize=(22, 16), facecolor=BG)
    fig.suptitle(
        f"{provider} Model Selection Guide  ·  {stats['total']} Models  ·  {stats['run_date']}",
        color=HEAD,
        fontsize=22,
        fontweight="bold",
        y=0.98,
    )

    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 100)

    # Build table rows by use case
    y_pos = 95
    row_height = 5

    # Header
    ax.text(0.5, y_pos, "USE CASE", fontsize=12, fontweight="bold", color=HEAD, ha="left")
    ax.text(3.5, y_pos, "RECOMMENDED MODEL", fontsize=12, fontweight="bold", color=HEAD, ha="left")
    ax.text(7.0, y_pos, "DETAILS", fontsize=12, fontweight="bold", color=HEAD, ha="left")

    # Header line
    ax.plot([0.3, 9.7], [y_pos - 0.8, y_pos - 0.8], color=GRID, linewidth=2)
    y_pos -= 3

    # Add each use case section
    for use_case in sorted(use_case_groups.keys()):
        models = use_case_groups[use_case]
        # Find recommended model (latest and marked as recommended)
        recommended = None
        for m in sorted(models, key=lambda x: x.get("is_latest", False), reverse=True):
            if "[RECOMMENDED]" in m.get("recommendation", ""):
                recommended = m
                break
        if not recommended:
            recommended = models[0]

        # Get model details
        model_id = recommended.get("model_id", "N/A")[:30]
        family = recommended.get("family", "N/A")
        rec = recommended.get("recommendation", "[GOOD]")
        color = recommended.get("rec_color", "#3b82f6")
        count = len(models)

        # Use case label (left)
        ax.text(0.5, y_pos, use_case, fontsize=11, fontweight="bold", color=color, ha="left",
                bbox=dict(boxstyle="round,pad=0.4", facecolor=CARD, edgecolor=color, linewidth=1.5))

        # Recommended model (middle)
        ax.text(3.5, y_pos + 0.7, model_id, fontsize=10, fontweight="bold", color=HEAD, ha="left", family="monospace")
        ax.text(3.5, y_pos - 0.5, rec, fontsize=9, color="white",
                bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.85))

        # Details (right)
        details = f"{count} model{'s' if count > 1 else ''} in {family}"
        ax.text(7.0, y_pos, details, fontsize=9, color=TEXT, ha="left", style="italic")

        # Separator line
        ax.plot([0.3, 9.7], [y_pos - 2, y_pos - 2], color=GRID, linewidth=0.5, linestyle="--")
        y_pos -= 4.5

    # Legend at bottom
    legend_y = 8
    ax.text(0.5, legend_y + 2, "Recommendation Tiers:", fontsize=10, fontweight="bold", color=HEAD, ha="left")

    legend_items = [
        ("[RECOMMENDED]", "#1e40af", "Best choice for production"),
        ("[GOOD]", "#10b981", "Solid, proven models"),
        ("[NICHE]", "#f59e0b", "Specialized use cases"),
        ("[DEPRECATED]", "#6b7280", "Legacy, avoid for new projects"),
    ]

    for i, (badge, col, desc) in enumerate(legend_items):
        x = 0.5 + (i % 2) * 5
        y = legend_y - (i // 2) * 1.5
        ax.text(x, y, badge, fontsize=8, color="white", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor=col, alpha=0.9))
        ax.text(x + 1.5, y, desc, fontsize=8, color=TEXT, ha="left")

    chart_path = f"{OUTPUT_DIR}/model_chart_{ts}.png"
    try:
        fig.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor=BG, edgecolor="none")
        plt.close()

        # Validate file was created and has size
        if not os.path.exists(chart_path) or os.path.getsize(chart_path) == 0:
            raise ValueError(f"Chart file created but is empty or missing: {chart_path}")

        file_size_mb = os.path.getsize(chart_path) / (1024 * 1024)
        print(f"✅ Chart PNG: {chart_path} ({file_size_mb:.2f} MB)")
        return chart_path
    except Exception as e:
        print(f"❌ Failed to generate chart: {e}")
        raise


# ── Step 3: Generate Mermaid diagram ──────────────────────────────────────────
def generate_mermaid_png(stats):
    """Generate Mermaid diagram and convert to PNG, with matplotlib fallback."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    provider = stats["provider"]

    # Build mermaid mindmap - organized by use case groups
    lines = ["mindmap", f"  root(({provider} AI Models: {stats['total']} Total))"]

    # Group families by use case
    use_case_groups = {}
    for fam, mods in stats["families"].items():
        latest = stats["latest_per_family"].get(fam, {})
        use_case = latest.get("use_case", "Other")
        if use_case not in use_case_groups:
            use_case_groups[use_case] = []
        use_case_groups[use_case].append((fam, mods, latest))

    # Build mindmap organized by use case
    for use_case in sorted(use_case_groups.keys()):
        lines.append(f"    {use_case}")
        for fam, mods, latest in sorted(use_case_groups[use_case], key=lambda x: len(x[1]), reverse=True):
            count = len(mods)
            rec = latest.get("recommendation", "").replace("[", "").replace("]", "")
            lid = latest.get("model_id", "?")[:30]
            # Use text indicators instead of emoji
            status = rec if rec else "Active"
            lines.append(f"      {fam} ({count})")
            lines.append(f"        {status}")
            lines.append(f"        Latest: {lid}")

    mermaid_text = "\n".join(lines)
    mmd_path = f"{OUTPUT_DIR}/model_mindmap_{ts}.mmd"
    png_path = f"{OUTPUT_DIR}/model_mindmap_{ts}.png"

    with open(mmd_path, "w") as f:
        f.write(mermaid_text)
    print(f"   Mermaid markdown: {mmd_path}")

    # Try mermaid-cli (use full path or npx)
    mmdc_cmd = "mmdc"
    try:
        import shutil
        if not shutil.which("mmdc"):
            mmdc_cmd = "npx --yes @mermaid-js/mermaid-cli mmdc"
    except:
        pass

    ret = os.system(
        f"{mmdc_cmd} -i {mmd_path} -o {png_path} -t default -b '#ffffff' -w 1400 -H 900 2>/dev/null"
    )
    if ret != 0 or not os.path.exists(png_path):
        print("   ⚠️  mermaid-cli unavailable, using matplotlib text fallback...")
        png_path = _text_diagram_fallback(stats, ts)

    if not os.path.exists(png_path) or os.path.getsize(png_path) == 0:
        raise ValueError(f"Diagram failed to generate: {png_path}")

    file_size_mb = os.path.getsize(png_path) / (1024 * 1024)
    print(f"✅ Mermaid PNG: {png_path} ({file_size_mb:.2f} MB)")
    return png_path, mmd_path


def _text_diagram_fallback(stats, ts):
    """Render a clean text-based class diagram as PNG using matplotlib."""
    BG, CARD, TEXT, HEAD = "#ffffff", "#f0f4f8", "#1e40af", "#0f172a"
    provider = stats["provider"]

    families = sorted(stats["families"].keys())
    n_fam = len(families)
    cols = 4
    rows = (n_fam + cols - 1) // cols

    fig, ax = plt.subplots(figsize=(20, max(10, rows * 2.5)), facecolor=BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_xlim(0, cols)
    ax.set_ylim(-rows - 0.5, 1.5)

    ax.text(
        cols / 2,
        1.2,
        f"{provider} AI MODEL LANDSCAPE",
        ha="center",
        va="center",
        fontsize=20,
        fontweight="bold",
        color="#0f172a",
        fontfamily="sans-serif",
    )
    ax.text(
        cols / 2,
        0.8,
        f"{stats['total']} Total Models  ·  {stats['family_count']} Families",
        ha="center",
        va="center",
        fontsize=13,
        color="#1e40af",
        fontfamily="sans-serif",
    )

    for i, fam in enumerate(families):
        mods = stats["families"][fam]
        count = len(mods)
        latest = stats["latest_per_family"].get(fam, {})
        lid = latest.get("model_id", "?")[:20]
        use_case = latest.get("use_case", "General")
        rec = latest.get("recommendation", "")
        rec_color = latest.get("rec_color", "#3b82f6")

        col = i % cols
        row = -(i // cols) - 1
        cx, cy = col + 0.5, row + 0.5

        rect = mpatches.FancyBboxPatch(
            (col + 0.05, row + 0.08),
            0.88,
            0.82,
            boxstyle="round,pad=0.02",
            facecolor=CARD,
            edgecolor=rec_color,
            linewidth=2.5,
        )
        ax.add_patch(rect)

        ax.text(
            cx,
            cy + 0.32,
            f"{fam}",
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="#0f172a",
            fontfamily="sans-serif",
        )
        ax.text(
            cx, cy + 0.13, use_case, ha="center", va="center",
            fontsize=8, fontweight="bold", color=rec_color, fontfamily="sans-serif"
        )
        ax.text(
            cx, cy - 0.02, f"{count} models", ha="center", va="center", fontsize=7, color="#64748b", fontfamily="sans-serif"
        )
        ax.text(
            cx, cy - 0.16, rec, ha="center", va="center", fontsize=7,
            color="white", bbox=dict(boxstyle="round,pad=0.25", facecolor=rec_color, alpha=0.9)
        )
        ax.text(cx, cy - 0.32, lid, ha="center", va="center", fontsize=6, color="#94a3b8", fontfamily="monospace")

    legend_patches = [
        mpatches.Patch(color="#1e40af", label="[RECOMMENDED] - Production-ready, latest"),
        mpatches.Patch(color="#10b981", label="[GOOD] - Stable, proven"),
        mpatches.Patch(color="#f59e0b", label="[NICHE] - Specialized use cases"),
        mpatches.Patch(color="#6b7280", label="[DEPRECATED] - Legacy models"),
    ]
    fig.legend(
        handles=legend_patches,
        loc="lower center",
        ncol=2,
        facecolor="#f8fafc",
        edgecolor="#cbd5e1",
        labelcolor="#0f172a",
        fontsize=9,
        framealpha=0.95,
        bbox_to_anchor=(0.5, 0.04),
    )

    png_path = f"{OUTPUT_DIR}/model_diagram_{ts}.png"
    try:
        fig.savefig(png_path, dpi=150, bbox_inches="tight", facecolor=BG)
        plt.close()

        if not os.path.exists(png_path) or os.path.getsize(png_path) == 0:
            raise ValueError(f"Diagram fallback failed: {png_path}")

        return png_path
    except Exception as e:
        print(f"❌ Diagram fallback failed: {e}")
        raise


# ── Step 4: Generate post content via Gemini ──────────────────────────────────
def generate_content(stats):
    """Generate LinkedIn post and Medium article using Gemini."""
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not set")
        raise ValueError("GEMINI_API_KEY required")
    provider = stats["provider"]

    families_summary = ", ".join(
        f"{fam}({len(mods)})"
        for fam, mods in sorted(stats["families"].items(), key=lambda x: len(x[1]), reverse=True)[:8]
    )
    high_conf = len(stats["conf_buckets"]["high"])
    low_conf = len(stats["conf_buckets"]["low"])

    # LinkedIn post
    high_pct = int((high_conf / stats['total']) * 100) if stats['total'] > 0 else 0
    low_pct = int((low_conf / stats['total']) * 100) if stats['total'] > 0 else 0

    li_prompt = f"""Write a professional, compelling LinkedIn post announcing an AI model discovery analysis.

CONTEXT:
We just completed an automated discovery of all {provider} AI models using a LangGraph agent with semantic enrichment via Gemini.

RECOMMENDATION TIERS:
- ⭐ RECOMMENDED: Latest, production-ready flagship models
- ✓ GOOD: Stable, proven, actively maintained models
- ⚠ NICHE: Specialized use cases, less common
- ⚠ DEPRECATED: Legacy models, approach with caution

MODEL CATEGORIES BY USE CASE:
- Complex Reasoning: o-series, gpt-4 (for advanced tasks)
- Versatile Multimodal: gpt-4o (best all-around)
- Fast & Cost-Effective: gpt-4o-mini, gpt-3.5-turbo
- Semantic Search: text-embedding (RAG, similarity)
- Image Generation: DALL-E (creative work)
- Speech Processing: Whisper (transcription), TTS (synthesis)
- Content Moderation: moderation APIs

FINDINGS TO HIGHLIGHT:
- Total Models: {stats['total']} models across {stats['family_count']} distinct families
- Recommended: {high_conf} flagship models ready for production
- Good/Stable: {len(stats['conf_buckets']['medium'])} proven models for most use cases
- Niche/Specialized: {low_conf} specialized or experimental models
- Discovery Method: Automated LangGraph agent + comprehensive use-case classification
- Storage: Complete dataset in BigQuery for team analysis

STRUCTURE (MUST FOLLOW):
1. Hook: Start with impressive discovery scale (119 models, 17 families)
2. Value: Explain what this discovery enables (clear model selection, risk reduction)
3. Classification: Highlight recommended production models vs specialized/niche
4. Discovery Method: Mention LangGraph automation + BigQuery accessibility
5. CTA: Ask about their model selection challenges
6. Hashtags: #AI #LLM #ModelOps #GenerativeAI #OpenAI

TONE: Professional, actionable, data-driven. Focus on HELPING developers choose.
LENGTH: 700-850 characters (3-4 sentences)
COMPLETENESS: Ensure every sentence is complete. NO truncation. Check it ends properly.

Key points to include:
- {high_conf} production-ready flagship models identified
- {stats['total']} total models mapped across all use cases
- Automated discovery reduces manual model research
- BigQuery makes data accessible to teams

Example style:
"We automated discovery of OpenAI's {stats['total']} models across {stats['family_count']} families, identifying which are production-ready... [insight]... [question] #AI #LLM"

Write only the LinkedIn post text, nothing else."""

    li_resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": li_prompt}]}],
            "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.85, "topP": 0.9}
        }
    )
    li_resp.raise_for_status()
    resp_data = li_resp.json()
    if "candidates" not in resp_data or not resp_data["candidates"]:
        raise ValueError(f"Invalid Gemini response: {resp_data}")
    linkedin_text = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Validate completion - ensure it ends with proper punctuation
    if not linkedin_text or len(linkedin_text) < 150:
        print(f"⚠️  Warning: LinkedIn response too short ({len(linkedin_text)} chars)")
    if linkedin_text and not linkedin_text[-1] in '.!?)#':
        linkedin_text = linkedin_text.rsplit(' ', 1)[0] + '.'
        print(f"⚠️  Truncated incomplete sentence, added period")

    # Medium article (markdown)
    rows_md = "\n".join(
        f"| `{fam}` | {len(mods)} | "
        f"`{stats['latest_per_family'][fam].get('model_id','?')}` | "
        f"{stats['latest_per_family'][fam].get('model_purpose','—')[:60]} |"
        for fam, mods in sorted(stats["families"].items(), key=lambda x: len(x[1]), reverse=True)
    )
    families_table = "| Family | Count | Latest Model | Purpose |\n|--------|-------|--------------|--------|\n" + rows_md

    high_models_list = "\n".join(
        f"- **`{m['model_id']}`** — {m.get('model_purpose','')[:80]}"
        for m in sorted(stats["conf_buckets"]["high"], key=lambda x: x.get("family", ""))[:15]
    )
    low_models_list = "\n".join(
        f"- **`{m['model_id']}`** (family: {m.get('family','?')}, "
        f"confidence: {m.get('confidence',0):.2f})"
        for m in stats["conf_buckets"]["low"][:10]
    )

    med_high_pct = int((high_conf / stats['total']) * 100) if stats['total'] > 0 else 0

    med_prompt = f"""Write a comprehensive, highly technical Medium article about this AI model discovery analysis.

CRITICAL DATA (use throughout article):
- Provider: {provider}
- Run Date: {stats['run_date']}
- Total Models: {stats['total']} across {stats['family_count']} families
- Verified (≥80%): {high_conf} models ({med_high_pct}%)
- Partial: {len(stats['conf_buckets']['medium'])} models
- Needs Review (<50%): {low_conf} models

MUST INCLUDE (verbatim, in dedicated section):
Family Distribution Table:
{families_table}

Top Verified Models:
{high_models_list}

Models Under Review:
{low_models_list}

ARTICLE STRUCTURE (MANDATORY):

Title: {provider} AI Model Landscape: The Complete {stats['total']}-Model Discovery Report

## Executive Summary
- Why this discovery matters: {provider} has exploded from a handful of models to {stats['total']} in {stats['family_count']} families
- Key finding: Only {med_high_pct}% are well-documented, creating deployment risk
- Who needs this: ML engineers, platform teams, AI architects choosing which models to use
- Your role: Mapping the entire landscape with automated discovery to reduce selection paralysis

## How We Discovered All {stats['total']} Models
- Method: LangGraph agent with autonomous discovery logic
- Enrichment: Gemini API semantic analysis for documentation quality
- Validation: 3-step confidence scoring (API docs → official pages → Gemini inference)
- Storage: BigQuery for team-wide access and historical tracking
- Timeline: Execution time and number of API calls made

## The {stats['family_count']} Model Families Explained
[Include the families table above]
Analysis of patterns:
- Which families are production-grade (stable, well-docs, frequently updated)
- Which are experimental (newer, less stable)
- Deprecation patterns and upgrade paths
- Generational progression (gpt-3.5 → gpt-4 → gpt-4-turbo)

## Quality Metrics: Why {high_conf} Models Are Verified ✅
[List top {min(10, high_conf)} verified models]
- What makes them safe for production
- API stability track record
- Documentation completeness
- Update frequency and backward compatibility
- Recommended use cases

## The {low_conf} Models Flagged for Review ⚠️
[List top {min(5, low_conf)} under-documented models]
- Common reasons for low confidence scores
- What information is missing (purpose? examples? pricing?)
- Risk of deploying with incomplete docs
- Recommendations: contact support, run pilot, monitor closely

## Key Insights from {stats['total']} Models
1. The {provider} strategy: breadth (17 families) vs depth (multiple versions per family)
2. Confidence distribution tells a story: {med_high_pct}% verified means gaps in their API documentation
3. Deprecation patterns: which old models are retired vs maintained
4. Innovation velocity: new model releases suggest shifting focus toward [area]
5. Market positioning: models map to OpenAI's product categories

## Practical Model Selection Guide
For your use case, choose:
- **Text generation**: [recommended models] - production-stable, well-documented
- **Code generation**: [recommended models] - specific considerations
- **Function calling**: [recommended models] - reliability notes
- **Vision/multimodal**: [recommended models] - capability matrix
- **Embeddings**: [recommended models] - performance vs cost trade-offs
- **Avoid or research first**: [models with low confidence]

## Operational Recommendations
1. Adopt automated model discovery (refresh quarterly minimum)
2. Maintain model compatibility matrix in your infrastructure
3. Set deprecation alerts for models you depend on
4. Test new model releases in staging before production
5. Document your model selection rationale

## The Bigger Picture: Beyond {provider}
- Why single-provider dependence is risky
- Multi-provider model landscape (Anthropic, Google, Meta)
- Building provider-agnostic applications
- Future: automating discovery across all providers

## Conclusion: Act on This Data
Don't let the {stats['total']}-model landscape paralyze your decisions. This discovery gives you:
- ✅ Confidence to choose verified models
- ✅ Awareness of documentation gaps
- ✅ Framework for ongoing model tracking
- ✅ Data to justify architectural decisions

Next step: adopt automated discovery in your organization.

REQUIREMENTS:
- 2000-2500 words (comprehensive, substantial)
- Highly technical but accessible tone
- Data-driven with specific numbers throughout
- Include practical recommendations readers can act on today
- Use subheadings for scannability
- Ensure EVERY SECTION IS COMPLETE (no truncation)
- Professional Medium-style writing with narrative flow"""

    med_resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": med_prompt}]}],
            "generationConfig": {"maxOutputTokens": 5000, "temperature": 0.75, "topP": 0.9}
        }
    )
    med_resp.raise_for_status()
    resp_data = med_resp.json()
    if "candidates" not in resp_data or not resp_data["candidates"]:
        raise ValueError(f"Invalid Gemini response: {resp_data}")
    medium_content = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()

    return linkedin_text, medium_content


# ── Step 5: Post to LinkedIn ──────────────────────────────────────────────────
def post_linkedin(text, image_path, token=LINKEDIN_TOKEN, urn=LINKEDIN_PERSON_URN):
    """Post to LinkedIn with image."""
    if not token or not urn:
        print("⚠️  LINKEDIN_ACCESS_TOKEN or LINKEDIN_AUTHOR_URN not set — skipping")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # Register image upload
    r = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers,
        json={
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": urn,
                "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}],
            }
        },
    )
    r.raise_for_status()
    upload_url = r.json()["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"][
        "uploadUrl"
    ]
    asset_urn = r.json()["value"]["asset"]

    # Upload image
    with open(image_path, "rb") as img:
        requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "image/png"},
            data=img,
        ).raise_for_status()

    # Create post
    r2 = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json={
            "author": urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "description": {"text": "AI Model Discovery Report"},
                            "media": asset_urn,
                            "title": {"text": "Model Discovery Chart"},
                        }
                    ],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        },
    )
    r2.raise_for_status()
    post_id = r2.json().get("id", "")
    url = f"https://www.linkedin.com/feed/update/{post_id}/"
    print(f"✅ LinkedIn posted: {url}")
    return url


# ── Step 6: Post to Medium ────────────────────────────────────────────────────
def post_medium(content, title, token=MEDIUM_TOKEN, user_id=MEDIUM_USER_ID):
    """Post to Medium or save as draft."""
    if not token or not user_id:
        print("⚠️  MEDIUM_TOKEN or MEDIUM_USER_ID not set — saving to file instead")
        path = f"{OUTPUT_DIR}/medium_draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(path, "w") as f:
            f.write(f"# {title}\n\n{content}")
        print(f"📄 Medium draft saved: {path}")
        return path

    r = requests.post(
        f"https://api.medium.com/v1/users/{user_id}/posts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "title": title,
            "contentFormat": "markdown",
            "content": content,
            "tags": ["AI", "LLM", "OpenAI", "ModelOps", "GenerativeAI"],
            "publishStatus": "draft",
        },
    )
    r.raise_for_status()
    url = r.json().get("data", {}).get("url", "")
    print(f"✅ Medium draft created: {url}")
    return url


# ── Step 7: Update README ─────────────────────────────────────────────────────
def update_readme(stats, li_url, med_url):
    """Update README.md with latest run badge."""
    readme_path = "README.md"
    badge_block = f"""
## 📊 Latest Model Discovery Run

| Field | Value |
|-------|-------|
| Provider | {stats['provider']} |
| Run Date | {stats['run_date']} |
| Total Models | {stats['total']} |
| Families | {stats['family_count']} |
| High Confidence | {len(stats['conf_buckets']['high'])} |
| Needs Review | {len(stats['conf_buckets']['low'])} |
| LinkedIn Post | {li_url or 'N/A'} |
| Medium Article | {med_url or 'N/A'} |

"""
    if os.path.exists(readme_path):
        with open(readme_path) as f:
            content = f.read()
        import re

        # Replace existing badge block if present
        content = re.sub(
            r"## 📊 Latest Model Discovery Run.*?(?=\n## |\Z)",
            badge_block.strip() + "\n\n",
            content,
            flags=re.DOTALL,
        )
        if "## 📊 Latest Model Discovery Run" not in content:
            content += "\n" + badge_block
    else:
        content = badge_block

    with open(readme_path, "w") as f:
        f.write(content)
    print(f"✅ README.md updated")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else "agents/model_discovery_candidates_openai.json"

    print(f"\n{'='*60}")
    print(f"  DISCOVERY PUBLISHER")
    print(f"  Input: {json_path}")
    print(f"{'='*60}\n")

    print("📦 Parsing JSON...")
    stats = parse_json(json_path)
    print(f"   {stats['provider']} · {stats['total']} models · {stats['family_count']} families\n")

    print("📊 Generating charts...")
    chart_png = generate_charts(stats)

    print("\n🗺  Generating model diagram...")
    diagram_png, diagram_mmd = generate_mermaid_png(stats)

    print("\n✍️  Generating content via Gemini...")
    linkedin_text, medium_content = generate_content(stats)

    # Save text files locally always
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    li_path = f"{OUTPUT_DIR}/linkedin_post_{ts}.txt"
    med_path_local = f"{OUTPUT_DIR}/medium_article_{ts}.md"
    with open(li_path, "w") as f:
        f.write(linkedin_text)
    with open(med_path_local, "w") as f:
        f.write(medium_content)
    print(f"   LinkedIn text saved: {li_path}")
    print(f"   Medium draft saved:  {med_path_local}")

    print("\n🔗 Posting to LinkedIn...")
    li_url = post_linkedin(linkedin_text, chart_png)

    print("\n📝 Posting to Medium...")
    title = f"{stats['provider']} Has {stats['total']} Active AI Models — Full Discovery Report {stats['run_date']}"
    med_url = post_medium(medium_content, title)

    print("\n📖 Updating README...")
    update_readme(stats, li_url, med_url)

    print(f"\n{'='*60}")
    print("  PUBLISH COMPLETE")
    print(f"{'='*60}")
    print(f"📊 Chart:        {chart_png}")
    print(f"🗺  Diagram:      {diagram_png}")
    print(f"📝 LinkedIn:     {li_url or li_path}")
    print(f"📄 Medium:       {med_url or med_path_local}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
