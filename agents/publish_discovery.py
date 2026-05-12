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


# ── Step 1: Parse JSON ────────────────────────────────────────────────────────
def parse_json(path):
    """Parse discovery JSON and compute statistics."""
    with open(path) as f:
        data = json.load(f)

    models = data.get("normalized_models", [])
    provider = data.get("target_provider", "openai").upper()
    run_id = data.get("run_id", datetime.now().isoformat())
    run_date = run_id[:10] if len(run_id) >= 10 else datetime.now().strftime("%Y-%m-%d")

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


# ── Step 2: Generate PNG charts ───────────────────────────────────────────────
def generate_charts(stats):
    """Generate comprehensive 4-panel dark-themed chart."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    provider = stats["provider"]
    BG = "#0d1117"
    CARD = "#161b22"
    GRID = "#21262d"
    TEXT = "#c9d1d9"
    HEAD = "#f0f6fc"
    COLORS = ["#00d4aa", "#4fa3e0", "#f0a500", "#ff4d6d", "#bf5af2", "#ff9f0a", "#30d158"]

    fig = plt.figure(figsize=(20, 14), facecolor=BG)
    fig.suptitle(
        f"{provider} AI Model Landscape  ·  {stats['total']} Models  ·  {stats['run_date']}",
        color=HEAD,
        fontsize=18,
        fontweight="bold",
        y=0.98,
    )

    gs = fig.add_gridspec(2, 3, hspace=0.45, wspace=0.35, left=0.06, right=0.97, top=0.92, bottom=0.08)

    # ── Chart 1: Models per family (horizontal bar) ──
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.set_facecolor(CARD)
    fam_names = sorted(stats["families"].keys(), key=lambda x: len(stats["families"][x]))
    fam_counts = [len(stats["families"][f]) for f in fam_names]
    bar_colors = []
    for fam in fam_names:
        mods = stats["families"][fam]
        avg = sum(m.get("semantic_confidence", 0) for m in mods) / len(mods)
        bar_colors.append("#00d4aa" if avg >= 0.8 else "#f0a500" if avg >= 0.5 else "#ff4d6d")
    bars = ax1.barh(fam_names, fam_counts, color=bar_colors, edgecolor=GRID, height=0.65)
    ax1.set_facecolor(CARD)
    ax1.set_xlabel("Number of Models", color=TEXT, fontsize=11)
    ax1.set_title("Models per Family", color=HEAD, fontsize=13, pad=10)
    ax1.tick_params(colors=TEXT, labelsize=9)
    ax1.spines[:].set_color(GRID)
    ax1.set_xlim(0, max(fam_counts) * 1.18 if fam_counts else 1)
    for bar, count in zip(bars, fam_counts):
        ax1.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            va="center",
            color=TEXT,
            fontsize=9,
        )
    ax1.grid(axis="x", color=GRID, linewidth=0.5)

    # ── Chart 2: Release stage pie ──
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.set_facecolor(CARD)
    sc = stats["stage_counts"]
    stage_colors_map = {
        "stable": "#00d4aa",
        "versioned": "#4fa3e0",
        "preview": "#f0a500",
        "deprecated": "#ff4d6d",
        "unknown": "#6e7681",
    }
    labels = list(sc.keys())
    sizes = list(sc.values())
    pcolors = [stage_colors_map.get(l, "#6e7681") for l in labels]
    wedges, texts, autos = ax2.pie(
        sizes,
        labels=labels,
        colors=pcolors,
        autopct="%1.0f%%",
        pctdistance=0.75,
        textprops={"color": TEXT, "fontsize": 9},
    )
    for a in autos:
        a.set_fontsize(8)
        a.set_color(HEAD)
    ax2.set_title("Release Stage Distribution", color=HEAD, fontsize=13, pad=10)

    # ── Chart 3: Purpose breakdown (donut) ──
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor(CARD)
    pc = stats["purpose_counts"]
    p_labels = list(pc.keys())
    p_sizes = list(pc.values())
    p_colors = COLORS[: len(p_labels)]
    wedges2, _, autos2 = ax3.pie(
        p_sizes,
        labels=p_labels,
        colors=p_colors,
        autopct="%1.0f%%",
        pctdistance=0.78,
        wedgeprops={"width": 0.5},
        textprops={"color": TEXT, "fontsize": 8},
    )
    for a in autos2:
        a.set_fontsize(7)
        a.set_color(HEAD)
    ax3.set_title("Model Purpose Breakdown", color=HEAD, fontsize=13, pad=10)

    # ── Chart 4: Confidence distribution (stacked bar per family) ──
    ax4 = fig.add_subplot(gs[1, 1:])
    ax4.set_facecolor(CARD)
    top10_fams = sorted(stats["families"].keys(), key=lambda x: len(stats["families"][x]), reverse=True)[
        :10
    ]
    highs = [sum(1 for m in stats["families"][f] if m.get("semantic_confidence", 0) >= 0.8) for f in top10_fams]
    mediums = [
        sum(1 for m in stats["families"][f] if 0.5 <= m.get("semantic_confidence", 0) < 0.8)
        for f in top10_fams
    ]
    lows = [sum(1 for m in stats["families"][f] if m.get("semantic_confidence", 0) < 0.5) for f in top10_fams]
    x = range(len(top10_fams))
    ax4.bar(x, highs, label="High conf (≥0.8)", color="#00d4aa", edgecolor=GRID)
    ax4.bar(x, mediums, label="Medium conf (0.5–0.8)", color="#f0a500", edgecolor=GRID, bottom=highs)
    ax4.bar(
        x,
        lows,
        label="Low conf (<0.5)",
        color="#ff4d6d",
        edgecolor=GRID,
        bottom=[h + m for h, m in zip(highs, mediums)],
    )
    ax4.set_xticks(list(x))
    ax4.set_xticklabels(top10_fams, rotation=35, ha="right", color=TEXT, fontsize=8)
    ax4.tick_params(colors=TEXT)
    ax4.spines[:].set_color(GRID)
    ax4.set_title("Confidence Quality (Top 10 Families)", color=HEAD, fontsize=13, pad=10)
    ax4.legend(fontsize=8, facecolor=CARD, edgecolor=GRID, labelcolor=TEXT)
    ax4.grid(axis="y", color=GRID, linewidth=0.5)
    ax4.set_ylabel("Model Count", color=TEXT, fontsize=10)

    # ── Footer legend ──
    patches = [
        mpatches.Patch(color="#00d4aa", label="Well documented"),
        mpatches.Patch(color="#f0a500", label="Partial docs"),
        mpatches.Patch(color="#ff4d6d", label="Needs review"),
    ]
    fig.legend(
        handles=patches,
        loc="lower center",
        ncol=3,
        facecolor=CARD,
        edgecolor=GRID,
        labelcolor=TEXT,
        fontsize=10,
        bbox_to_anchor=(0.5, 0.01),
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

    # Build mermaid mindmap
    lines = ["mindmap", f"  root(({provider}\\n{stats['total']} Models))"]
    for fam in sorted(stats["families"].keys()):
        mods = stats["families"][fam]
        count = len(mods)
        latest = stats["latest_per_family"].get(fam, {})
        lid = latest.get("model_id", "?")
        avg_c = sum(m.get("semantic_confidence", 0) for m in mods) / count
        icon = "✅" if avg_c >= 0.8 else "⚠️" if avg_c >= 0.5 else "❌"
        lines.append(f"    {fam}({icon} {fam}\\n{count} models)")
        lines.append(f"      Latest: {lid}")

    mermaid_text = "\n".join(lines)
    mmd_path = f"{OUTPUT_DIR}/model_mindmap_{ts}.mmd"
    png_path = f"{OUTPUT_DIR}/model_mindmap_{ts}.png"

    with open(mmd_path, "w") as f:
        f.write(mermaid_text)
    print(f"   Mermaid markdown: {mmd_path}")

    # Try mermaid-cli
    ret = os.system(
        f"npx --yes @mermaid-js/mermaid-cli mmdc -i {mmd_path} -o {png_path} -t dark -b '#0d1117' -w 1400 -H 900 2>/dev/null"
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
    BG, CARD, TEXT, HEAD = "#0d1117", "#161b22", "#c9d1d9", "#f0f6fc"
    provider = stats["provider"]

    families = sorted(stats["families"].keys())
    n_fam = len(families)
    cols = 4
    rows = (n_fam + cols - 1) // cols

    fig, ax = plt.subplots(figsize=(20, max(8, rows * 2.5)), facecolor=BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_xlim(0, cols)
    ax.set_ylim(-rows - 0.5, 0.8)

    ax.text(
        cols / 2,
        0.5,
        f"{provider} MODEL FAMILIES  ·  {stats['total']} Models",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color=HEAD,
        fontfamily="monospace",
    )

    for i, fam in enumerate(families):
        mods = stats["families"][fam]
        count = len(mods)
        latest = stats["latest_per_family"].get(fam, {})
        lid = latest.get("model_id", "?")[:28]
        avg_c = sum(m.get("semantic_confidence", 0) for m in mods) / count
        border = "#00d4aa" if avg_c >= 0.8 else "#f0a500" if avg_c >= 0.5 else "#ff4d6d"
        icon = "✅" if avg_c >= 0.8 else "⚠️" if avg_c >= 0.5 else "❌"

        col = i % cols
        row = -(i // cols) - 1
        cx, cy = col + 0.5, row + 0.5

        rect = mpatches.FancyBboxPatch(
            (col + 0.05, row + 0.08),
            0.88,
            0.82,
            boxstyle="round,pad=0.02",
            facecolor=CARD,
            edgecolor=border,
            linewidth=1.5,
        )
        ax.add_patch(rect)
        ax.text(
            cx,
            cy + 0.28,
            f"{icon} {fam}",
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
            color=HEAD,
            fontfamily="monospace",
        )
        ax.text(
            cx, cy + 0.08, f"{count} models", ha="center", va="center", fontsize=8, color=TEXT, fontfamily="monospace"
        )
        ax.text(cx, cy - 0.1, lid, ha="center", va="center", fontsize=7, color=border, fontfamily="monospace")
        ax.text(
            cx, cy - 0.27, f"conf: {avg_c:.1f}", ha="center", va="center", fontsize=7, color=TEXT, fontfamily="monospace"
        )

    legend_patches = [
        mpatches.Patch(color="#00d4aa", label="High confidence (≥0.8)"),
        mpatches.Patch(color="#f0a500", label="Medium confidence"),
        mpatches.Patch(color="#ff4d6d", label="Needs review (<0.5)"),
    ]
    fig.legend(
        handles=legend_patches,
        loc="lower center",
        ncol=3,
        facecolor=CARD,
        edgecolor="#21262d",
        labelcolor=TEXT,
        fontsize=9,
        bbox_to_anchor=(0.5, 0.0),
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
    li_prompt = f"""Write a short LinkedIn post (max 800 chars, 2-3 sentences).

Facts: {provider} - {stats['total']} models, {stats['family_count']} families. LangGraph agent discovery. BigQuery storage. {high_conf} well-documented, {low_conf} need review.

Format: Hook → brief insight → engagement question. End with #AI #LLMOps #ModelDiscovery."""

    li_resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": li_prompt}]}],
            "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.7, "topP": 0.95}
        }
    )
    li_resp.raise_for_status()
    resp_data = li_resp.json()
    if "candidates" not in resp_data or not resp_data["candidates"]:
        raise ValueError(f"Invalid Gemini response: {resp_data}")
    linkedin_text = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
    if not linkedin_text or len(linkedin_text) < 50:
        print(f"⚠️  Warning: LinkedIn response too short ({len(linkedin_text)} chars), may be incomplete")

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
        f"confidence: {m.get('semantic_confidence',0):.2f})"
        for m in stats["conf_buckets"]["low"][:10]
    )

    med_prompt = f"""Write a Medium newsletter article in Markdown about this AI model discovery run.

Data:
- Provider: {provider}
- Run date: {stats['run_date']}
- Total models: {stats['total']}
- Families: {stats['family_count']}
- High confidence: {high_conf} | Low confidence: {low_conf}

Families table (include this verbatim):
{families_table}

High confidence models (include top 10):
{high_models_list}

Low confidence / needs review (include top 5):
{low_models_list}

Structure:
# {provider} Has {stats['total']} Active AI Models — Here's the Full Map

## Introduction (2 paragraphs — why this matters)

## How We Discovered These Models
(LangGraph agent, BigQuery storage, semantic enrichment via Gemini)

## The Model Families ({stats['family_count']} Distinct Families)
(include the families table)

## What's Well-Documented ✅
(list top 10 high-confidence models with purpose)

## What Needs Review ⚠️
(list low-confidence models and why they matter)

## Key Insights
(3-4 bullet insights from the data)

## What This Means for Developers
(practical advice on which models to use)

## Conclusion + Call to Action

Tags line at end: AI, LLM, OpenAI, ModelOps, GenerativeAI

Keep it informative, data-driven, developer-friendly. ~800 words."""

    med_resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": med_prompt}]}],
            "generationConfig": {"maxOutputTokens": 3000, "temperature": 0.7, "topP": 0.95}
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
