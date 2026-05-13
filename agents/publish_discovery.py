#!/usr/bin/env python3
"""
publish_discovery.py
Reads model discovery JSON → generates charts → optional publish to LinkedIn + Medium
Usage:
  python agents/publish_discovery.py agents/model_discovery_candidates_openai.json
  python agents/publish_discovery.py agents/model_discovery_candidates_openai.json --publish
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
USE_CASE_MAP = [
    {"key": "complex_reasoning", "title": "Complex Reasoning", "icon": "CR", "color": "#3d70b2", "desc": "Deep reasoning and long-horizon tasks"},
    {"key": "fast_chat", "title": "Fast Chat", "icon": "FC", "color": "#1192e8", "desc": "Low-latency conversational workloads"},
    {"key": "image_generation", "title": "Image Generation", "icon": "IG", "color": "#8a3ffc", "desc": "Image creation and editing"},
    {"key": "video_generation", "title": "Video Generation", "icon": "VG", "color": "#a56eff", "desc": "Video generation and transformation"},
    {"key": "speech_to_text", "title": "Speech-to-Text", "icon": "ST", "color": "#198038", "desc": "Audio transcription and recognition"},
    {"key": "text_to_speech", "title": "Text-to-Speech", "icon": "TS", "color": "#24a148", "desc": "Natural speech synthesis"},
    {"key": "embeddings", "title": "Embeddings", "icon": "EM", "color": "#007d79", "desc": "Semantic search and retrieval"},
    {"key": "content_moderation", "title": "Content Moderation", "icon": "CM", "color": "#525252", "desc": "Safety and policy compliance"},
    {"key": "realtime_audio", "title": "Realtime Audio", "icon": "RA", "color": "#ee538b", "desc": "Streaming voice interactions"},
    {"key": "multimodal_vision", "title": "Multimodal Vision", "icon": "MV", "color": "#fa4d56", "desc": "Vision understanding and multimodal IO"},
    {"key": "legacy", "title": "Legacy/Deprecated", "icon": "LG", "color": "#6f6f6f", "desc": "Older or phased-out model families"},
    {"key": "fine_tuning", "title": "Fine-tuning Base", "icon": "FT", "color": "#ff832b", "desc": "Base models for customization"},
]

USE_CASE_KEYWORDS = {
    "complex_reasoning": ["o-series", "o1", "o3", "o4", "reasoning"],
    "fast_chat": ["gpt-3.5", "gpt-4o-mini", "mini"],
    "image_generation": ["dall-e", "image", "gpt-image"],
    "video_generation": ["sora", "video", "veo"],
    "speech_to_text": ["whisper", "speech"],
    "text_to_speech": ["tts", "text-to-speech"],
    "embeddings": ["embedding", "text-embedding"],
    "content_moderation": ["moderation"],
    "realtime_audio": ["gpt-realtime", "realtime", "audio", "gpt-audio"],
    "multimodal_vision": ["gpt-4o", "gpt-4", "vision", "multimodal"],
    "legacy": ["davinci", "babbage", "curie", "legacy"],
    "fine_tuning": ["gpt-3.5-turbo", "base"],
}

def classify_model_to_usecase(model):
    """Classify a model to one of 12 use-case categories using keyword matching."""
    model_id = model.get("model_id", "").lower()
    family = model.get("family", "").lower()
    combined = f"{model_id} {family}".lower()

    for use_case, keywords in USE_CASE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined:
                return use_case
    return "Other"


def classify_models(stats):
    grouped = defaultdict(list)
    for m in stats["all_models"]:
        grouped[m.get("use_case", "Other")].append(m)
    return grouped




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
    """4x3 grid of use-case cards using GridSpec. No manual coordinates."""
    from matplotlib.gridspec import GridSpec
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    categorized = classify_models(stats)

    BG = "#ffffff"
    CARD_BG = "#f4f4f4"
    BORDER = "#e0e0e0"
    TEXT = "#161616"
    SUBTEXT = "#525252"

    fig = plt.figure(figsize=(20, 16), facecolor=BG)
    gs = GridSpec(
        nrows=5, ncols=4,
        height_ratios=[1.2, 0.8, 3, 3, 3],
        hspace=0.35, wspace=0.25,
        left=0.04, right=0.96, top=0.97, bottom=0.04
    )

    ax_header = fig.add_subplot(gs[0, :])
    ax_header.axis("off")
    rect = mpatches.Rectangle((0, 0), 1, 1, transform=ax_header.transAxes, facecolor="#0f62fe", zorder=0)
    ax_header.add_patch(rect)
    ax_header.text(0.5, 0.5, f"{stats['provider']} AI Model Discovery Dashboard",
                   transform=ax_header.transAxes, ha="center", va="center",
                   fontsize=28, fontweight="bold", color="#ffffff", zorder=1)

    metrics = [
        (str(stats["total"]), "Total Models"),
        (str(stats["family_count"]), "Families"),
        (str(len([m for m in stats["all_models"] if m.get("recommendation") == "[RECOMMENDED]"])), "Recommended"),
        (str(len(stats["conf_buckets"]["high"])), "High Confidence"),
    ]
    for i, (val, label) in enumerate(metrics):
        ax_m = fig.add_subplot(gs[1, i])
        ax_m.axis("off")
        ax_m.text(0.5, 0.65, val, ha="center", va="center", fontsize=32, fontweight="bold", color="#0f62fe", transform=ax_m.transAxes)
        ax_m.text(0.5, 0.2, label, ha="center", va="center", fontsize=11, color=SUBTEXT, transform=ax_m.transAxes)

    for idx, uc in enumerate(USE_CASE_MAP):
        row = 2 + idx // 4
        col = idx % 4
        ax = fig.add_subplot(gs[row, col])
        _render_card(ax, uc, categorized.get(uc["key"], []), CARD_BG, BORDER, TEXT, SUBTEXT)

    chart_path = f"{OUTPUT_DIR}/model_chart_{ts}.png"
    fig.savefig(chart_path, dpi=130, bbox_inches="tight", facecolor=BG, edgecolor="none")
    plt.close()
    print(f"✅ Chart PNG: {chart_path}")
    return chart_path


def _render_card(ax, uc, models, CARD_BG, BORDER, TEXT, SUBTEXT):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    count = len(models)
    if count == 0:
        badge_text, badge_color = "EMPTY", "#a8a8a8"
    elif uc["key"] in ("legacy", "fine_tuning"):
        badge_text, badge_color = "DEPRECATED", "#da1e28"
    else:
        high_in = sum(1 for m in models if m.get("semantic_confidence", 0) >= 0.8)
        has_latest = any(m.get("is_latest") for m in models)
        if has_latest and high_in > 0:
            badge_text, badge_color = "RECOMMENDED", "#0f62fe"
        elif high_in > 0:
            badge_text, badge_color = "GOOD", "#198038"
        else:
            badge_text, badge_color = "NICHE", "#8a3ffc"

    card = mpatches.FancyBboxPatch((0.1, 0.1), 9.8, 9.8, boxstyle="round,pad=0.05,rounding_size=0.3",
                                   facecolor=CARD_BG, edgecolor=BORDER, linewidth=1.5)
    ax.add_patch(card)
    accent = mpatches.Rectangle((0.1, 8.2), 9.8, 1.7, facecolor=uc["color"], edgecolor="none")
    ax.add_patch(accent)
    ax.text(0.5, 9.05, uc["icon"], fontsize=20, va="center", color="#ffffff")
    ax.text(1.4, 9.05, uc["title"], fontsize=13, fontweight="bold", va="center", color="#ffffff")

    badge = mpatches.FancyBboxPatch((7.3, 8.5), 2.4, 1.0, boxstyle="round,pad=0.02,rounding_size=0.15",
                                    facecolor=badge_color, edgecolor="none")
    ax.add_patch(badge)
    ax.text(8.5, 9.0, badge_text, fontsize=8, fontweight="bold", ha="center", va="center", color="#ffffff")

    if models:
        best = max(models, key=lambda m: (m.get("is_latest", False), m.get("semantic_confidence", 0)))
        mid = best.get("model_id", "")
        if len(mid) > 24:
            mid = mid[:22] + ".."
        ax.text(0.5, 7.3, "Recommended Model:", fontsize=9, color=SUBTEXT)
        ax.text(0.5, 6.3, mid, fontsize=12, fontweight="bold", color=TEXT, family="monospace")
        ax.text(0.5, 5.0, f"Family: {best.get('family', '—')}", fontsize=10, color=SUBTEXT, style="italic")
        ax.text(0.5, 4.0, f"Available Models: {count}", fontsize=10, color=TEXT, fontweight="bold")
        desc_box = mpatches.FancyBboxPatch((0.5, 0.7), 9.0, 1.8, boxstyle="round,pad=0.05,rounding_size=0.15",
                                           facecolor="#e8e8e8", edgecolor="none")
        ax.add_patch(desc_box)
        ax.text(5.0, 1.6, uc["desc"], ha="center", va="center", fontsize=9, color=SUBTEXT, style="italic", wrap=True)
    else:
        ax.text(5.0, 5.0, "No models in this category", ha="center", va="center", fontsize=10, color=SUBTEXT, style="italic")


# ── Step 3: Generate Mermaid diagram (grouped by use-case) ──────────────────────
def generate_mermaid_png(stats):
    """Mindmap: category → latest model → status. One node per item."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    categorized = classify_models(stats)
    lines = [
        "%%{init: {'theme':'base','themeVariables':{'primaryColor':'#0f62fe','primaryTextColor':'#ffffff','primaryBorderColor':'#0353e9','lineColor':'#525252','fontFamily':'Helvetica'}}}%%",
        "mindmap",
        f"  root(({stats['provider']}<br/>{stats['total']} Models<br/>{stats['family_count']} Families))"
    ]
    for uc in USE_CASE_MAP:
        models = categorized.get(uc["key"], [])
        if not models:
            continue
        count = len(models)
        if uc["key"] in ("legacy", "fine_tuning"):
            status = "DEPRECATED"
        else:
            high_in = sum(1 for m in models if m.get("semantic_confidence", 0) >= 0.8)
            has_latest = any(m.get("is_latest") for m in models)
            if has_latest and high_in > 0:
                status = "RECOMMENDED"
            elif high_in > 0:
                status = "GOOD"
            else:
                status = "NICHE"
        best = max(models, key=lambda m: (m.get("is_latest", False), m.get("semantic_confidence", 0)))
        bid = best.get("model_id", "?")
        bfam = best.get("family", "?")
        cat_id = uc["key"].replace("_", "")
        lines.append(f"    {cat_id}[{uc['icon']} {uc['title']}<br/>{count} models]")
        lines.append(f"      {cat_id}_model[Latest: {bid}]")
        lines.append(f"      {cat_id}_fam[Family: {bfam}]")
        lines.append(f"      {cat_id}_status[Status: {status}]")
    mermaid_text = "\n".join(lines)
    mmd_path = f"{OUTPUT_DIR}/model_mindmap_{ts}.mmd"
    png_path = f"{OUTPUT_DIR}/model_mindmap_{ts}.png"
    with open(mmd_path, "w") as f:
        f.write(mermaid_text)
    print(f"\n=== MERMAID PREVIEW ===\n{mermaid_text}\n=====================\n")
    ret = os.system(
        f"npx --yes @mermaid-js/mermaid-cli mmdc -i {mmd_path} -o {png_path} -t default -b white -w 2400 -H 1600 2>/dev/null"
    )
    if ret != 0 or not os.path.exists(png_path):
        print("⚠️ mermaid-cli failed, using matplotlib fallback")
        png_path = _matplotlib_mindmap_fallback(stats, categorized, ts)
    print(f"✅ Mindmap: {png_path}")
    return png_path, mmd_path


def _matplotlib_mindmap_fallback(stats, categorized, ts):
    import math
    fig, ax = plt.subplots(figsize=(18, 14), facecolor="#ffffff")
    ax.set_xlim(-12, 12)
    ax.set_ylim(-10, 10)
    ax.axis("off")
    ax.set_aspect("equal")

    center = mpatches.Circle((0, 0), 1.8, facecolor="#0f62fe", edgecolor="none")
    ax.add_patch(center)
    ax.text(0, 0.3, stats["provider"], ha="center", va="center", fontsize=14, fontweight="bold", color="#ffffff")
    ax.text(0, -0.3, f"{stats['total']} Models", ha="center", va="center", fontsize=10, color="#ffffff")
    ax.text(0, -0.7, f"{stats['family_count']} Families", ha="center", va="center", fontsize=10, color="#ffffff")

    active = [uc for uc in USE_CASE_MAP if categorized.get(uc["key"])]
    n = len(active)
    for i, uc in enumerate(active):
        angle = (2 * math.pi * i / n) - math.pi / 2
        cx = 7 * math.cos(angle)
        cy = 7 * math.sin(angle)
        models = categorized[uc["key"]]
        best = max(models, key=lambda m: (m.get("is_latest", False), m.get("semantic_confidence", 0)))
        ax.plot([0, cx * 0.4], [0, cy * 0.4], color=uc["color"], linewidth=2, alpha=0.6)
        bubble = mpatches.FancyBboxPatch((cx - 2.2, cy - 0.8), 4.4, 1.6,
                                         boxstyle="round,pad=0.1,rounding_size=0.3",
                                         facecolor=uc["color"], edgecolor="none")
        ax.add_patch(bubble)
        ax.text(cx, cy + 0.3, f"{uc['icon']} {uc['title']}", ha="center", va="center", fontsize=10, fontweight="bold", color="#ffffff")
        ax.text(cx, cy - 0.3, f"{len(models)} models · {best.get('model_id', '')[:18]}", ha="center", va="center", fontsize=8, color="#ffffff")

    path = f"{OUTPUT_DIR}/model_mindmap_{ts}.png"
    fig.savefig(path, dpi=130, bbox_inches="tight", facecolor="#ffffff")
    plt.close()
    return path


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
    publish_mode = "--publish" in sys.argv
    json_path = sys.argv[1] if len(sys.argv) > 1 else "agents/model_discovery_candidates_openai.json"
    if json_path == "--publish":
        json_path = "agents/model_discovery_candidates_openai.json"

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

    if not publish_mode:
        print("\n⏸  Visual generation complete. Publish steps skipped (use --publish to enable posting).")
        print(f"📊 Chart:   {chart_png}")
        print(f"🗺  Diagram: {diagram_png}")
        print(f"📝 Mermaid: {diagram_mmd}")
        return

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
