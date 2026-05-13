#!/usr/bin/env python3
"""
publish_discovery.py
Reads model discovery JSON → generates charts → posts to LinkedIn + Medium
Usage: python agents/publish_discovery.py agents/model_discovery_candidates_openai.json
"""

import json
import os
import sys
import re
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

# ── USE_CASE_MAP: 12 Core Model Categories ────────────────────────────────────
USE_CASE_MAP = {
    "Complex Reasoning": ["o-series", "o1", "o3", "o4", "reasoning"],
    "Fast Chat": ["gpt-3.5", "gpt-4o-mini", "mini"],
    "Image Generation": ["dall-e", "image", "gpt-image"],
    "Video Generation": ["sora", "video", "veo"],
    "Speech-to-Text": ["whisper", "speech"],
    "Text-to-Speech": ["tts", "text-to-speech"],
    "Embeddings": ["embedding", "text-embedding"],
    "Content Moderation": ["moderation"],
    "Realtime Audio": ["gpt-realtime", "realtime", "audio", "gpt-audio"],
    "Multimodal Vision": ["gpt-4o", "gpt-4", "vision", "multimodal"],
    "Legacy/Deprecated": ["davinci", "babbage", "curie", "legacy"],
    "Fine-tuning Base": ["gpt-3.5-turbo", "base"],
}

def classify_model_to_usecase(model):
    """Classify a model to one of 12 use-case categories using keyword matching."""
    model_id = model.get("model_id", "").lower()
    family = model.get("family", "").lower()
    combined = f"{model_id} {family}".lower()

    for use_case, keywords in USE_CASE_MAP.items():
        for keyword in keywords:
            if keyword in combined:
                return use_case
    return "Other"




# ── Step 1: Parse JSON ────────────────────────────────────────────────────────
def parse_json(path):
    """Parse discovery JSON and compute statistics using enriched_models."""
    with open(path) as f:
        data = json.load(f)

    # CRITICAL: Use enriched_models which has semantic_confidence (0.3-0.9 = enrichment quality)
    # NOT normalized_models which has confidence: 1.0 (API verified)
    models = data.get("enriched_models", [])
    if not models:
        print("⚠️  WARNING: enriched_models not found, falling back to normalized_models")
        models = data.get("normalized_models", [])

    provider = data.get("target_provider", "openai").upper()
    run_id = data.get("run_id", datetime.now().isoformat())
    run_date = run_id[:10] if len(run_id) >= 10 else datetime.now().strftime("%Y-%m-%d")

    print(f"\n[DEBUG] Loaded {len(models)} models from {'enriched_models' if data.get('enriched_models') else 'normalized_models'}")
    if models:
        sample_confs = [m.get("semantic_confidence", m.get("confidence", 0)) for m in models[:5]]
        print(f"[DEBUG] Sample semantic_confidence values: {sample_confs}")

    # Enrich each model with use_case and recommendation
    for m in models:
        semantic_conf = m.get("semantic_confidence", m.get("confidence", 0))
        is_latest = m.get("is_latest", False)
        is_active = m.get("is_active", True)

        # Classify to one of 12 use-cases
        use_case = classify_model_to_usecase(m)
        m["use_case"] = use_case

        # Determine recommendation based on semantic_confidence
        if semantic_conf >= 0.8 and is_latest and is_active:
            rec = "[RECOMMENDED]"
            color = "#0f62fe"  # IBM Blue
        elif semantic_conf >= 0.8 and is_active:
            rec = "[GOOD]"
            color = "#198038"  # IBM Green
        elif semantic_conf < 0.5 or not is_active:
            rec = "[DEPRECATED]"
            color = "#da1e28"  # IBM Red
        else:
            rec = "[NICHE]"
            color = "#8a3ffc"  # IBM Purple

        m["semantic_confidence"] = semantic_conf
        m["recommendation"] = rec
        m["rec_color"] = color

    # Group by family
    families = defaultdict(list)
    for m in models:
        families[m["family"]].append(m)

    # Find latest per family
    latest_per_family = {}
    for fam, mlist in families.items():
        latest = [m for m in mlist if m.get("is_latest")]
        latest_per_family[fam] = (
            latest[0]
            if latest
            else sorted(mlist, key=lambda x: x.get("discovered_at", ""), reverse=True)[0]
        )

    # Compute confidence buckets using semantic_confidence
    stage_counts = defaultdict(int)
    conf_buckets = {"high": [], "medium": [], "low": []}
    for m in models:
        stage_counts[m.get("release_stage", "unknown")] += 1
        semantic_conf = m.get("semantic_confidence", 0)
        if semantic_conf >= 0.8:
            conf_buckets["high"].append(m)
        elif semantic_conf >= 0.5:
            conf_buckets["medium"].append(m)
        else:
            conf_buckets["low"].append(m)

    print(f"\n[STATS] High confidence (≥0.8): {len(conf_buckets['high'])}")
    print(f"[STATS] Medium confidence (0.5-0.8): {len(conf_buckets['medium'])}")
    print(f"[STATS] Low confidence (<0.5): {len(conf_buckets['low'])}")

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
        "all_models": models,
    }


# ── Step 2: Generate Dashboard-Style Model Selection Guide (12-card grid) ──────
def generate_charts(stats):
    """Generate 12-card grid dashboard (4 cols × 3 rows) on white background."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    provider = stats["provider"]

    # Color palette (IBM Carbon)
    BG = "#ffffff"
    CARD = "#f8fafc"
    GRID = "#cbd5e1"
    TEXT = "#0f172a"
    HEAD = "#1e293b"
    ACCENT = "#0284c7"
    REC_COLOR = "#0f62fe"    # IBM Blue (Recommended)
    GOOD_COLOR = "#198038"   # IBM Green
    NICHE_COLOR = "#8a3ffc"  # IBM Purple
    DEPRECATED_COLOR = "#da1e28"  # IBM Red

    # Group by use-case
    use_case_groups = defaultdict(list)
    for m in stats["all_models"]:
        uc = m.get("use_case", "Other")
        use_case_groups[uc].append(m)

    # Sort use-cases for consistent grid layout
    sorted_use_cases = sorted(use_case_groups.keys())

    # 12-card grid: 4 cols × 3 rows
    num_cols = 4
    num_rows = 3
    fig_height = 14
    fig = plt.figure(figsize=(20, fig_height), facecolor=BG)

    # Header
    header_box = mpatches.Rectangle(
        (0, 0.94), 1, 0.06, transform=fig.transFigure, facecolor=ACCENT, edgecolor="none", zorder=0
    )
    fig.patches.append(header_box)

    fig.text(0.5, 0.975, f"{provider} AI Model Discovery Dashboard",
             ha="center", fontsize=28, fontweight="bold", color="#ffffff")

    # Metrics row
    metrics_y = 0.89
    metrics = [
        (f"{stats['total']} Models", "Total"),
        (f"{stats['family_count']} Families", "Categories"),
        (f"{len(stats['conf_buckets']['high'])} Recommended", "Production-ready"),
    ]
    metric_x = 0.1
    for metric, desc in metrics:
        fig.text(metric_x, metrics_y + 0.025, metric, fontsize=14, fontweight="bold", color=TEXT)
        fig.text(metric_x, metrics_y - 0.01, desc, fontsize=9, color=GRID)
        metric_x += 0.28
    fig.text(0.92, metrics_y, f"Updated: {stats['run_date']}", fontsize=9, color=GRID, ha="right")

    # Create grid layout
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.set_xlim(0, num_cols)
    ax.set_ylim(0, num_rows)

    card_width = 0.23
    card_height = 0.28
    margin_x = 0.01
    margin_y = 0.01

    # Draw 12 cards
    for idx in range(num_cols * num_rows):
        col = idx % num_cols
        row = idx // num_cols

        x = margin_x + col * (card_width + margin_x * 2)
        y = num_rows - 1 - row * (card_height + margin_y * 2) - card_height

        if idx < len(sorted_use_cases):
            use_case = sorted_use_cases[idx]
            models = use_case_groups[use_case]

            # Find recommended model
            recommended = None
            for m in sorted(models, key=lambda x: x.get("is_latest", False), reverse=True):
                if "[RECOMMENDED]" in m.get("recommendation", ""):
                    recommended = m
                    break
            if not recommended:
                for m in sorted(models, key=lambda x: x.get("recommendation") == "[GOOD]", reverse=True):
                    recommended = m
                    break
            if not recommended:
                recommended = models[0]

            # Get recommendation color
            rec = recommended.get("recommendation", "").replace("[", "").replace("]", "")
            if rec == "RECOMMENDED":
                rec_color = REC_COLOR
            elif rec == "GOOD":
                rec_color = GOOD_COLOR
            elif rec == "DEPRECATED":
                rec_color = DEPRECATED_COLOR
            else:
                rec_color = NICHE_COLOR

            model_id = recommended.get("model_id", "?")[:20]
            count = len(models)

            # Card background
            card_box = mpatches.FancyBboxPatch(
                (x, y), card_width, card_height, boxstyle="round,pad=0.005",
                facecolor=CARD, edgecolor=GRID, linewidth=0.8
            )
            ax.add_patch(card_box)

            # Top colored bar
            top_bar = mpatches.Rectangle(
                (x, y + card_height - 0.04), card_width, 0.04,
                facecolor=rec_color, edgecolor="none"
            )
            ax.add_patch(top_bar)

            # Title
            ax.text(x + 0.005, y + card_height - 0.015, use_case.upper(),
                   fontsize=8, fontweight="bold", color="#ffffff", ha="left", va="center")

            # Recommendation badge
            ax.text(x + card_width - 0.005, y + card_height - 0.015, rec,
                   fontsize=6, color="#ffffff", fontweight="bold", ha="right", va="center")

            # Model name
            ax.text(x + 0.005, y + 0.18, model_id,
                   fontsize=7, color=HEAD, fontweight="bold", ha="left", family="monospace")

            # Count
            ax.text(x + 0.005, y + 0.12, f"{count} models",
                   fontsize=6, color=TEXT, ha="left")

            # Status
            ax.text(x + 0.005, y + 0.06, f"Status: {rec}",
                   fontsize=5, color=rec_color, ha="left", fontweight="bold")
        else:
            # Empty placeholder card
            card_box = mpatches.FancyBboxPatch(
                (x, y), card_width, card_height, boxstyle="round,pad=0.005",
                facecolor="#f0f4f8", edgecolor="#e2e8f0", linewidth=0.8, linestyle="--"
            )
            ax.add_patch(card_box)
            ax.text(x + card_width/2, y + card_height/2, "—",
                   fontsize=12, color="#cbd5e1", ha="center", va="center")

    chart_path = f"{OUTPUT_DIR}/model_chart_{ts}.png"
    try:
        fig.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor=BG)
        plt.close()

        if not os.path.exists(chart_path) or os.path.getsize(chart_path) == 0:
            raise ValueError(f"Chart file empty: {chart_path}")

        file_size_mb = os.path.getsize(chart_path) / (1024 * 1024)
        print(f"✅ Chart PNG: {chart_path} ({file_size_mb:.2f} MB)")
        return chart_path
    except Exception as e:
        print(f"❌ Failed to generate chart: {e}")
        raise


# ── Step 3: Generate Mermaid diagram (grouped by use-case) ──────────────────────
def generate_mermaid_png(stats):
    """Generate Mermaid mindmap grouped by use-case categories."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    provider = stats["provider"]

    # Group families by use-case
    use_case_groups = defaultdict(list)
    for m in stats["all_models"]:
        use_case = m.get("use_case", "Other")
        family = m.get("family", "")
        if family not in [fam for fam, _ in use_case_groups[use_case]]:
            use_case_groups[use_case].append((family, len(stats["families"].get(family, []))))

    # Build mindmap
    lines = ["mindmap", f"  root(({provider}<br/>{stats['total']} Models<br/>{stats['family_count']} Families))"]

    for use_case in sorted(use_case_groups.keys()):
        lines.append(f"    {use_case}")
        for family, count in sorted(use_case_groups[use_case], key=lambda x: x[1], reverse=True):
            latest = stats["latest_per_family"].get(family, {})
            rec = latest.get("recommendation", "").replace("[", "").replace("]", "")
            lines.append(f"      {family} ({count})")
            if rec:
                lines.append(f"        {rec}")

    mermaid_config = """%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#dbeafe',
    'primaryBorderColor': '#60a5fa',
    'primaryTextColor': '#ffffff',
    'tertiaryColor': '#e0f2fe',
    'tertiaryBorderColor': '#0284c7',
    'tertiaryTextColor': '#ffffff',
    'fontSize': '14px',
    'fontFamily': 'Arial, sans-serif'
  }
}}%%
"""

    mermaid_text = mermaid_config + "\n" + "\n".join(lines)
    mmd_path = f"{OUTPUT_DIR}/model_mindmap_{ts}.mmd"
    png_path = f"{OUTPUT_DIR}/model_mindmap_{ts}.png"

    with open(mmd_path, "w") as f:
        f.write(mermaid_text)
    print(f"   Mermaid markdown: {mmd_path}")

    # Try mermaid-cli
    mmdc_cmd = "mmdc"
    try:
        import shutil
        if not shutil.which("mmdc"):
            mmdc_cmd = "npx --yes @mermaid-js/mermaid-cli mmdc"
    except:
        pass

    ret = os.system(f"{mmdc_cmd} -i {mmd_path} -o {png_path} -t default -b '#ffffff' -w 1400 -H 900 2>/dev/null")
    if ret != 0 or not os.path.exists(png_path):
        print("   ⚠️  mermaid-cli unavailable, using matplotlib fallback...")
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


# ── Step 3.5: Verify no hallucination (number consistency) ──────────────────────
def verify_no_hallucination(linkedin_text, medium_text, stats):
    """Verify that posts don't contain hallucinated/contradictory numbers."""
    total = str(stats["total"])
    families = str(stats["family_count"])

    errors = []

    # Check Medium strictly (long-form)
    med_total_matches = re.findall(rf'\b{total}\s+(?:models?|active\s+AI\s+models?|AI\s+models?)\b', medium_text, re.IGNORECASE)
    med_family_matches = re.findall(rf'\b{families}\s+(?:families?|model\s+families?)\b', medium_text, re.IGNORECASE)

    if not med_total_matches:
        errors.append(f"Medium doesn't mention {total} models")
    if not med_family_matches:
        errors.append(f"Medium doesn't mention {families} families")

    # Check for CONTRADICTORY numbers in Medium (e.g., says 110 instead of 109)
    wrong_totals_med = re.findall(r'\b(\d+)\s+(?:models?|AI\s+models?)\b', medium_text, re.IGNORECASE)
    for num in set(wrong_totals_med):
        if num != total and int(num) > 100:
            errors.append(f"Medium mentions {num} models but should be {total}")

    # LinkedIn can be more lenient (shorter form, may not mention families)
    li_total_matches = re.findall(rf'\b{total}\s+(?:models?|AI\s+models?)\b', linkedin_text, re.IGNORECASE)
    if not li_total_matches:
        errors.append(f"LinkedIn doesn't mention {total} models")

    wrong_totals_li = re.findall(r'\b(\d+)\s+(?:models?|AI\s+models?)\b', linkedin_text, re.IGNORECASE)
    for num in set(wrong_totals_li):
        if num != total and int(num) > 100:
            errors.append(f"LinkedIn mentions {num} models but should be {total}")

    if errors:
        print("\n❌ HALLUCINATION DETECTED:")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print(f"\n✅ Verification passed: {total} models, {families} families (consistent across posts)")
        return True


# ── Step 4: Generate post content via Gemini ──────────────────────────────────
def generate_content(stats):
    """Generate LinkedIn post and Medium article using Gemini with STRICT FACTS."""
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not set")
        raise ValueError("GEMINI_API_KEY required")
    provider = stats["provider"]

    high_conf = len(stats["conf_buckets"]["high"])
    medium_conf = len(stats["conf_buckets"]["medium"])
    low_conf = len(stats["conf_buckets"]["low"])

    # LinkedIn post with STRICT FACTS block
    li_prompt = f"""Write a personal, engaging LinkedIn post about building a model discovery agent.

STRICT FACTS (use ONLY these numbers, never hallucinate):
- Total models: {stats['total']}
- Model families: {stats['family_count']}
- High-confidence (production-ready): {high_conf}
- Medium-confidence (stable): {medium_conf}
- Low-confidence (experimental): {low_conf}
- Provider: {provider}
- Discovery method: Automated LangGraph agent
- Enrichment: Gemini API
- Storage: BigQuery
- Run date: {stats['run_date']}

STRUCTURE:
1. Personal hook: "I built an agent that..."
2. The numbers: Only use facts above (total, families, high-conf)
3. Why it matters: Developers need clarity on model landscape
4. Technical approach: LangGraph + Gemini + BigQuery
5. Call to action: What's YOUR biggest challenge?

TONE: Authentic, technical, not salesy
LENGTH: Max 1300 characters
CONSTRAINT: Only use numbers from STRICT FACTS block. Never mention specific model names unless in STRICT FACTS.

Write ONLY the post text, no commentary."""

    li_resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": li_prompt}]}],
            "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.8, "topP": 0.9}
        }
    )
    li_resp.raise_for_status()
    resp_data = li_resp.json()
    if "candidates" not in resp_data or not resp_data["candidates"]:
        raise ValueError(f"Invalid Gemini response: {resp_data}")
    linkedin_text = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()

    if not linkedin_text or len(linkedin_text) < 100:
        raise ValueError(f"LinkedIn post too short: {len(linkedin_text)} chars")

    # Medium article with STRICT FACTS and tables
    families_list = ", ".join(sorted(stats["families"].keys()))

    med_prompt = f"""Write a data-driven Medium article titled "How I Discovered All {provider}'s AI Models Automatically"

STRICT FACTS (use ONLY these, never hallucinate):
- Total models: {stats['total']}
- Model families: {stats['family_count']}
- High-confidence models (≥0.8): {high_conf}
- Medium-confidence models (0.5-0.8): {medium_conf}
- Low-confidence models (<0.5): {low_conf}
- Discovery source: {provider}'s /v1/models API (confidence: 1.0)
- Enrichment: Gemini API semantic analysis
- Storage: BigQuery
- Discovery date: {stats['run_date']}
- All families: {families_list}

ARTICLE STRUCTURE:

# How I Discovered All {provider}'s {stats['total']} AI Models Automatically

## TL;DR
- {provider} has {stats['total']} active AI models across {stats['family_count']} families
- {high_conf} models are production-ready, {medium_conf} are stable, {low_conf} need careful review
- Built automated discovery agent: LangGraph + Gemini enrichment + BigQuery
- Discovered on: {stats['run_date']}

## Why This Matters
The {provider} model ecosystem is massive and fragmented. Choosing between {stats['total']} models is overwhelming.

## The Discovery Method

I built a LangGraph agent that:
1. **Tier 1 (Official API)**: Queries {provider}'s /v1/models endpoint directly (100% verified)
2. **Enrichment**: Uses Gemini API to analyze each of {stats['total']} models
3. **Storage**: Persists everything in BigQuery for team access
4. **Confidence Scoring**: Semantic confidence 0-1.0 for each model

All {stats['total']} models came directly from the official API (confidence: 1.0).

## Model Confidence Distribution

| Confidence Level | Count | What It Means |
|------------------|-------|---------------|
| High (≥0.8) | {high_conf} | Production-ready, well-documented |
| Medium (0.5-0.8) | {medium_conf} | Stable but less comprehensive docs |
| Low (<0.5) | {low_conf} | Experimental or sparse documentation |
| **Total** | **{stats['total']}** | **All {provider} models** |

## All {stats['family_count']} Model Families

{families_list}

## Production-Ready Models ({high_conf} high-confidence)

These {high_conf} models are verified and production-ready:
- All with semantic confidence ≥0.8
- Full documentation available
- Safe for production use
- Regular updates from {provider}

## Models Needing Care ({low_conf} low-confidence)

These {low_conf} models have limited documentation:
- Semantic confidence <0.5
- Experimental or new releases
- Require careful evaluation before production
- Monitor for updates

## Key Insights

1. **Scale**: {stats['total']} models is a massive ecosystem
2. **Fragmentation**: {stats['family_count']} families provides specialization
3. **Documentation**: Clear correlation between confidence and production-readiness
4. **Automation**: Discovering this manually would take weeks
5. **Versioning**: Multiple variants across families

## Next Steps

1. **For Teams**: Import this data into your model selection matrix
2. **For Monitoring**: Re-run discovery quarterly to catch new releases
3. **For Decision-Making**: Use confidence scores to choose safe defaults
4. **For Production**: Always test even high-confidence models in staging

## The Tool

Source: {provider}'s {stats['total']} models from official API
Method: LangGraph agent with Gemini semantic enrichment
Storage: BigQuery
Runtime: Minutes (fully automated)

This is the future: automated, data-driven model ecosystem management.

---

**Data snapshot**: {stats['run_date']} | **Total models**: {stats['total']} | **Families**: {stats['family_count']}

Tags: AI, LLM, {provider}, ModelOps, Automation, BigQuery, Gemini"""

    med_resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": med_prompt}]}],
            "generationConfig": {"maxOutputTokens": 4000, "temperature": 0.7, "topP": 0.9}
        }
    )
    med_resp.raise_for_status()
    resp_data = med_resp.json()
    if "candidates" not in resp_data or not resp_data["candidates"]:
        raise ValueError(f"Invalid Gemini response: {resp_data}")
    medium_content = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()

    if not medium_content or len(medium_content) < 500:
        raise ValueError(f"Medium article too short: {len(medium_content)} chars")

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

    # Print summary statistics
    high = len(stats['conf_buckets']['high'])
    medium = len(stats['conf_buckets']['medium'])
    low = len(stats['conf_buckets']['low'])
    print(f"\n{'='*60}")
    print(f"SUMMARY STATISTICS")
    print(f"{'='*60}")
    print(f"✅ High Confidence (≥0.8): {high} models")
    print(f"⚠️  Medium Confidence (0.5-0.8): {medium} models")
    print(f"❌ Low Confidence (<0.5): {low} models")
    print(f"{'='*60}\n")

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

    # CRITICAL: Verify no hallucination before posting
    print("\n🔍 Verifying content for hallucinations...")
    if not verify_no_hallucination(linkedin_text, medium_content, stats):
        print("\n⛔ Verification FAILED. Posts contain hallucinated numbers. NOT POSTING.")
        print(f"\n   LinkedIn: {li_path}")
        print(f"   Medium:   {med_path_local}")
        print("   Review manually and fix before posting.")
        return

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
