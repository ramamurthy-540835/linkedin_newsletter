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
    """Parse discovery JSON and compute statistics using enriched_models."""
    with open(path) as f:
        data = json.load(f)

    # Use enriched_models which has semantic_confidence, fall back to normalized_models
    models = data.get("enriched_models", []) or data.get("normalized_models", [])
    provider = data.get("target_provider", "openai").upper()
    run_id = data.get("run_id", datetime.now().isoformat())
    run_date = run_id[:10] if len(run_id) >= 10 else datetime.now().strftime("%Y-%m-%d")

    print(f"\n[DEBUG] Loaded {len(models)} models from {'enriched_models' if data.get('enriched_models') else 'normalized_models'}")
    if models:
        sample_confs = [m.get("semantic_confidence", m.get("confidence", 0)) for m in models[:5]]
        print(f"[DEBUG] Sample semantic_confidence values: {sample_confs}")

    # Compute recommendation tier based on actual semantic_confidence
    for m in models:
        # Get actual semantic confidence from enriched data
        semantic_conf = m.get("semantic_confidence", m.get("confidence", 0))
        is_latest = m.get("is_latest", False)
        is_active = m.get("is_active", True)
        family = m.get("family", "").lower()
        model_id = m.get("model_id", "").lower()

        # Flagship families for RECOMMENDED tier
        flagship = ["gpt-5", "gpt-4o", "o-series", "text-embedding", "tts", "whisper", "dall-e"]
        is_flagship = any(f in family for f in flagship)

        # Determine recommendation based on semantic_confidence and other factors
        if is_latest and is_flagship and semantic_conf >= 0.8:
            rec = "[RECOMMENDED]"
            color = "#0f62fe"  # IBM Blue
        elif semantic_conf >= 0.8 and is_active:
            rec = "[GOOD]"
            color = "#198038"  # IBM Green
        elif "legacy" in family or "deprecated" in family or "babbage" in model_id or "davinci-002" in model_id:
            rec = "[DEPRECATED]"
            color = "#da1e28"  # IBM Red
        elif not is_active or semantic_conf < 0.5:
            rec = "[DEPRECATED]"
            color = "#da1e28"
        else:
            rec = "[NICHE]"
            color = "#8a3ffc"  # IBM Purple

        m["semantic_confidence"] = semantic_conf
        m["recommendation"] = rec
        m["rec_color"] = color
        # Store numeric score for backward compat
        rec_scores = {"[RECOMMENDED]": 1.0, "[GOOD]": 0.8, "[NICHE]": 0.5, "[DEPRECATED]": 0.2}
        m["enriched_confidence"] = rec_scores.get(rec, semantic_conf)

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
        c = m.get("semantic_confidence", 0)
        if c >= 0.8:
            conf_buckets["high"].append(m)
        elif c >= 0.5:
            conf_buckets["medium"].append(m)
        else:
            conf_buckets["low"].append(m)

    # Print stats for verification
    print(f"\n[STATS] High confidence (≥0.8): {len(conf_buckets['high'])}")
    print(f"[STATS] Medium confidence (0.5-0.8): {len(conf_buckets['medium'])}")
    print(f"[STATS] Low confidence (<0.5): {len(conf_buckets['low'])}")

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


# ── Step 2: Generate Dashboard-Style Model Selection Guide ────────────────────
def generate_charts(stats):
    """Generate a modern dashboard-style model selection guide with large cards."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    provider = stats["provider"]
    # Professional white/dark scheme for better readability
    BG = "#ffffff"  # Clean white background
    CARD = "#f8fafc"  # Very light card background
    CARD_DARK = "#e2e8f0"  # Darker card accent
    GRID = "#cbd5e1"  # Grid lines
    TEXT = "#0f172a"  # Dark text
    HEAD = "#1e293b"  # Dark headers
    ACCENT = "#0284c7"  # Professional blue
    SUCCESS = "#059669"  # Green for recommended

    # Group models by use case
    use_case_groups = {}
    for fam, mods in stats["families"].items():
        for m in mods:
            uc = m.get("use_case", "Other")
            if uc not in use_case_groups:
                use_case_groups[uc] = []
            use_case_groups[uc].append(m)

    # Create large, informative dashboard with bigger cards
    num_cols = 2  # 2 columns for larger cards
    num_rows = (len(use_case_groups) + num_cols - 1) // num_cols
    fig_height = max(14, num_rows * 3.8 + 3)
    fig = plt.figure(figsize=(20, fig_height), facecolor=BG)

    # Header section with gradient-like background
    header_box = mpatches.Rectangle(
        (0, 0.94), 1, 0.06,
        transform=fig.transFigure,
        facecolor=ACCENT,
        edgecolor="none",
        zorder=0,
    )
    fig.patches.append(header_box)

    # Top section with title and stats
    fig.text(
        0.5, 0.975,
        f"{provider} AI Model Discovery Dashboard",
        ha="center",
        fontsize=28,
        fontweight="bold",
        color="#ffffff",
    )

    # Key metrics in a clean row
    metrics_y = 0.89
    metrics = [
        (f"{stats['total']} Models", "Total in database"),
        (f"{len(use_case_groups)} Categories", "Use case types"),
        (f"{len(stats['conf_buckets']['high'])} Recommended", "Production-ready"),
    ]

    metric_x = 0.08
    for metric, desc in metrics:
        fig.text(metric_x, metrics_y + 0.025, metric, fontsize=14, fontweight="bold", color=TEXT)
        fig.text(metric_x, metrics_y - 0.01, desc, fontsize=9, color=GRID)
        metric_x += 0.3

    fig.text(0.92, metrics_y, f"Updated: {stats['run_date']}", fontsize=9, color=GRID, ha="right")

    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, num_rows * 4 + 1)

    # Larger card-based layout
    card_width = 4.6
    card_height = 3.6
    margin = 0.4
    padding = 0.3

    y_offset = num_rows * 4
    for idx, use_case in enumerate(sorted(use_case_groups.keys())):
        col = idx % num_cols
        row = idx // num_cols

        x = margin + col * (card_width + margin + 0.4)
        y = y_offset - row * (card_height + margin)

        models = use_case_groups[use_case]
        recommended = None
        for m in sorted(models, key=lambda x: x.get("is_latest", False), reverse=True):
            if "[RECOMMENDED]" in m.get("recommendation", ""):
                recommended = m
                break
        if not recommended:
            recommended = models[0]

        model_id = recommended.get("model_id", "?")[:24]
        rec = recommended.get("recommendation", "[GOOD]").replace("[", "").replace("]", "")
        rec_color = recommended.get("rec_color", ACCENT)
        if rec == "RECOMMENDED":
            rec_color = SUCCESS
        count = len(models)
        fam = recommended.get("family", "?")

        # Draw main card background
        card_box = mpatches.FancyBboxPatch(
            (x, y - card_height),
            card_width,
            card_height,
            boxstyle="round,pad=0.12",
            facecolor=CARD,
            edgecolor=GRID,
            linewidth=1.5,
        )
        ax.add_patch(card_box)

        # Colored top bar (accent)
        top_bar = mpatches.Rectangle(
            (x, y - 0.5),
            card_width,
            0.5,
            facecolor=rec_color,
            edgecolor="none",
        )
        ax.add_patch(top_bar)

        # Card title (use case) - in white on colored background
        ax.text(
            x + padding, y - 0.28,
            use_case.upper(),
            fontsize=12,
            fontweight="bold",
            color="#ffffff",
            ha="left",
        )

        # Status badge (right side of colored bar)
        ax.text(
            x + card_width - padding, y - 0.28,
            rec,
            fontsize=9,
            color="#ffffff",
            fontweight="bold",
            ha="right",
        )

        # Divider line
        ax.plot([x + padding, x + card_width - padding], [y - 0.65, y - 0.65], color=GRID, linewidth=1)

        # Main content area
        content_y = y - 1.0

        # Model info
        ax.text(
            x + padding, content_y,
            "Recommended Model:",
            fontsize=8,
            color=GRID,
            fontweight="bold",
            ha="left",
        )

        ax.text(
            x + padding, content_y - 0.4,
            model_id,
            fontsize=11,
            color=HEAD,
            fontweight="bold",
            ha="left",
            family="monospace",
        )

        # Family info
        ax.text(
            x + padding, content_y - 0.9,
            f"Family: {fam}",
            fontsize=9,
            color=TEXT,
            ha="left",
        )

        # Count with visual indicator
        ax.text(
            x + padding, content_y - 1.4,
            f"Available Models: {count}",
            fontsize=9,
            color=TEXT,
            fontweight="bold",
            ha="left",
        )

        # Bottom info box
        info_box = mpatches.FancyBboxPatch(
            (x + padding, y - card_height + 0.2),
            card_width - 2 * padding,
            0.3,
            boxstyle="round,pad=0.05",
            facecolor=CARD_DARK,
            edgecolor=GRID,
            linewidth=0.5,
        )
        ax.add_patch(info_box)

        ax.text(
            x + card_width / 2, y - card_height + 0.35,
            f"Perfect for {use_case.lower()} tasks",
            fontsize=8,
            color=TEXT,
            ha="center",
            style="italic",
        )

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
    use_case_groups = {}
    for fam, mods in stats["families"].items():
        latest = stats["latest_per_family"].get(fam, {})
        use_case = latest.get("use_case", "Other")
        if use_case not in use_case_groups:
            use_case_groups[use_case] = []
        use_case_groups[use_case].append((fam, mods, latest))

    num_categories = len(use_case_groups)
    # Use <br> for actual line breaks in Mermaid
    lines = ["mindmap", f"  root(({provider}<br/>{stats['total']} Models<br/>{num_categories} Categories))"]

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

    # Add Mermaid theme configuration for lighter blue colors with white bold text
    mermaid_config = """%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#dbeafe',
    'primaryBorderColor': '#60a5fa',
    'primaryTextColor': '#ffffff',
    'tertiaryColor': '#e0f2fe',
    'tertiaryBorderColor': '#0284c7',
    'tertiaryTextColor': '#ffffff',
    'fontSize': '16px',
    'fontFamily': 'sans-serif',
    'fontFamily': 'Arial, sans-serif',
    'primaryBoldTextColor': '#ffffff',
    'textBkgColor': '#ffffff'
  }
}}%%
"""

    mermaid_text = mermaid_config + "\n" + "\n".join(lines)
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

    li_prompt = f"""Write a personal, data-driven LinkedIn post about building a model discovery agent.

PERSONAL CONTEXT:
I built a LangGraph agent that automatically discovered and classified all {provider}'s AI models.
It uses Gemini API for semantic enrichment and stores everything in BigQuery.
Completely automated—no manual research needed.

ACTUAL DATA FROM THIS RUN:
- {stats['total']} total models discovered
- {stats['family_count']} model families identified
- {high_conf} models verified production-ready (≥80% confidence)
- {len(stats['conf_buckets']['medium'])} models stable but less documented
- {low_conf} models experimental or legacy
- {stats['families'].get('gpt-5', [])[:1] and len(stats['families']['gpt-5'])} GPT-5 variants (biggest family!)
- Key families: GPT-5 ({len(stats['families'].get('gpt-5', []))}), GPT-4o ({len(stats['families'].get('gpt-4o', []))}), Whisper, DALL-E, embeddings

MOST SURPRISING FINDING:
GPT-5 already has {len(stats['families'].get('gpt-5', []))} variant models in the wild—
more than I expected. Plus future-dated models like gpt-image-2-2026-04-21.

STRUCTURE:
1. Hook: Personal journey building the agent ("I built an agent that...")
2. Surprising finding: The scale and variants available
3. What it enables: Developers can now see what's actually available
4. Technical approach: LangGraph + Gemini semantic enrichment + BigQuery
5. Question: What's YOUR biggest challenge choosing models?

TONE: Genuine, technical, not sales-y. I actually built this.
LENGTH: Max 1300 characters, no markdown, plain text only
AVOID: Don't mention "0 models" or fake stats. Only use real numbers above.

Include:
- Personal "I built" angle (more credible than "we discovered")
- Actual surprising insight (the 38 GPT-5 variants)
- Actionable value (they can use this data too)
- Real challenge question

Write ONLY the post text, no extra commentary."""

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

    med_prompt = f"""Write a data-driven Medium article about OpenAI's 119-model landscape discovery.

ACTUAL FACTS ONLY (no hallucinations):
- Provider: {provider}
- Total models: {stats['total']}
- Families: {stats['family_count']}
- High-confidence (≥0.8): {high_conf} models
- Medium-confidence: {len(stats['conf_buckets']['medium'])} models
- Low-confidence: {low_conf} models
- Largest family: GPT-5 with {len(stats['families'].get('gpt-5', []))} models
- Discovery method: Automated LangGraph agent from OpenAI's /v1/models API endpoint
- Enrichment: Gemini API analyzed 119 models
- Storage: BigQuery
- Date: {stats['run_date']}

MODELS TABLE (use verbatim):
{families_table}

ARTICLE STRUCTURE - WRITE EXACTLY AS:

# OpenAI Just Released 119 Models—Here's the Complete Map

## TL;DR
- OpenAI now has {stats['total']} active AI models across {stats['family_count']} families
- GPT-5 family dominates with {len(stats['families'].get('gpt-5', []))} variants
- {high_conf} models are production-ready, {len(stats['conf_buckets']['medium'])} are stable, {low_conf} need careful review
- Discovery method: Automated agent → LangGraph + Gemini enrichment → BigQuery

## Why This Matters
OpenAI's model ecosystem has exploded. Developers need to know: which {stats['total']} models should actually use?

## The Discovery Method
Built a LangGraph agent that:
1. Queries OpenAI's /v1/models API endpoint (discovery_tier 1 = direct API)
2. Runs semantic enrichment with Gemini API on all {stats['total']} models
3. Stores complete data in BigQuery for team access
4. Computes confidence scores (trust level of model documentation)

All 119 models came directly from the official API with confidence: 1.0 (100% verified source).

## The 17 Model Families

{families_table}

**Key patterns:**
- GPT-5: {len(stats['families'].get('gpt-5', []))} models (experimental, newest)
- GPT-4o: {len(stats['families'].get('gpt-4o', []))} models (versatile, latest)
- Whisper: Speech-to-text
- Text-embedding-3: Best embeddings quality
- DALL-E 3: Image generation
- Sora: Video generation

## Production-Ready Models (High Confidence)

These {high_conf} models are verified production-ready:

| Use Case | Best Model | Why |
|----------|-----------|-----|
| Complex reasoning | gpt-5-chat-latest | Latest flagship |
| Fast chat | gpt-4o-mini | Cost-efficient |
| Image generation | dall-e-3 or chatgpt-image-latest | Latest versions |
| Embeddings | text-embedding-3-large | Best quality |
| Speech-to-text | whisper-1 | Only option |
| Text-to-speech | tts-1-hd | HD quality |
| Reasoning | o4-mini | Efficient variant |
| Moderation | omni-moderation-latest | Always latest |

## Models Requiring Further Research ({low_conf} low-confidence)

These models have sparse documentation:
{low_models_list if low_models_list else "- None flagged"}

## What's Experimental or Future-Dated
- gpt-realtime family (9 models) - real-time audio
- gpt-image-2-2026-04-21 - future-dated model
- gpt-audio family - audio processing
- sora-2-pro - pro video generation

## What's Deprecated
- Legacy family: davinci-002, babbage-002
- Status: avoid for new projects

## Key Insights
1. **Scale**: 119 models is massive. This matters because you're not choosing between 5 flagship models anymore.
2. **Fragmentation**: 17 families means specialization. There's a model for almost every job.
3. **Velocity**: The future-dated gpt-image-2 shows OpenAI pre-announces what's coming.
4. **Documentation**: High-confidence models are well-documented; experimental ones require careful evaluation.
5. **Versioning**: Multiple variants per family (e.g., 38 gpt-5 models) means lots of optimization options.

## Practical Recommendations
1. **Start here**: Use gpt-4o, whisper-1, text-embedding-3-large for 80% of use cases
2. **Experiment early**: Try gpt-realtime and gpt-audio families only if relevant to your product
3. **Avoid legacy**: Don't use davinci-002 or babbage-002 for new projects
4. **Monitor versions**: OpenAI releases new model variants frequently; check for latest
5. **Test before production**: Even production-ready models warrant staging tests

## How to Track This Going Forward
This discovery is a snapshot from {stats['run_date']}. Best practice:
- Run automated discovery quarterly
- Monitor for new model releases
- Track deprecation announcements
- Maintain a model selection matrix in your docs

## The Code
LangGraph agent that did this:
- Queries /v1/models API endpoint
- Enriches with Gemini semantic analysis
- Stores in BigQuery
- Runnable in ~minutes, not days

This is the future of model ecosystem management: automated, data-driven, accessible to teams.

## Final Takeaway
Knowing all {stats['total']} models exist is the first step. Knowing which 8-10 models handle 90% of use cases is the real win.

Tags: AI, LLM, OpenAI, MLOps, LangGraph, BigQuery, Gemini"""

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
