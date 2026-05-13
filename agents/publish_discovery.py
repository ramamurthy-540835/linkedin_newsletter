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

# Vertex AI imports (optional)
try:
    from google.cloud import aiplatform
    from vertexai.preview.vision_models import ImageGenerationModel # Specific Imagen model import
    import vertexai # Still need vertexai.init
    _HAS_VERTEX_AI = True
except ImportError:
    _HAS_VERTEX_AI = False
    print("WARNING: Google Cloud Vertex AI libraries not found. Imagen generation will be skipped.")

# Load .env file
load_dotenv("backend/.env.local")
load_dotenv("backend/.env")

# Global dictionary for easier USE_CASE_MAP lookup
USE_CASE_MAP_DICT = {}

# ── Config from env ───────────────────────────────────────────────────────────
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINKEDIN_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_AUTHOR_URN")
MEDIUM_TOKEN = os.getenv("MEDIUM_TOKEN")
MEDIUM_USER_ID = os.getenv("MEDIUM_USER_ID")
GCP_PROJECT = os.getenv("GCP_PROJECT", "ctoteam")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001")


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

# Populate the global dictionary for easy lookup
USE_CASE_MAP_DICT = {uc["key"]: uc for uc in USE_CASE_MAP}


def _classify_model(model):
    """Classify a model to one of 12 use-case categories using attributes."""
    model_id = model.get("model_id", "").lower()
    family = model.get("family", "").lower()
    model_purpose = model.get("model_purpose", "").lower()
    recommended_for = " ".join([r.lower() for r in model.get("recommended_for", [])])
    capabilities = " ".join([c.lower() for c in model.get("capabilities", [])])
    
    model_id_lower = model.get("model_id", "").lower()
    family_lower = model.get("family", "").lower()
    model_purpose_lower = model.get("model_purpose", "").lower()
    recommended_for_lower = " ".join([r.lower() for r in model.get("recommended_for", [])])
    capabilities_lower = " ".join([c.lower() for c in model.get("capabilities", [])])
    
    combined_text = f"{model_id_lower} {family_lower} {model_purpose_lower} {recommended_for_lower} {capabilities_lower}"

    # Priority 1: Specific modalities (use model_id where possible for precision)
    if "sora" in model_id_lower:
        return "video_generation"
    if "text-embedding" in model_id_lower:
        return "embeddings"
    if any(k in model_id_lower for k in ["gpt-image", "dall-e", "chatgpt-image"]):
        return "image_generation"
    if any(k in model_id_lower for k in ["whisper", "transcribe"]):
        return "speech_to_text"
    if "tts" in model_id_lower:
        return "text_to_speech"
    if any(k in model_id_lower for k in ["realtime", "audio-preview", "gpt-audio"]):
        return "realtime_audio"
    if "moderation" in model_id_lower:
        return "content_moderation"

    # Priority 2: Core LLM categories (by family)
    if family_lower in ["gpt-5", "o-series"]:
        return "complex_reasoning"
    if family_lower in ["gpt-4o", "gpt-4"]:
        return "multimodal_vision"

    # Priority 3: Legacy models
    if any(k in model_id_lower for k in ["babbage", "davinci"]) or family_lower == "gpt-3.5":
        return "legacy"
    
    # Priority 4: Fine-tuning Base (explicitly mentions fine-tuning in purpose/capabilities)
    if "fine-tuning" in capabilities_lower or "fine-tuning" in model_purpose_lower:
        return "fine_tuning"

    # Priority 5: Fast Chat (remaining chat-like models that haven't been classified)
    # Ensure this is a fallback for general chat, not specific modalities
    # The `combined_text` implicitly filters out modalities already caught by higher rules.
    if "chat" in combined_text or "mini" in model_id_lower or "nano" in model_id_lower:
        return "fast_chat"

    return "Other"


def _score_model(model):
    """Scores a model for recommendation within its use case."""
    score = 0
    if model.get("is_latest", False):
        score += 100
    
    semantic_conf = model.get("semantic_confidence", 0)
    score += int(semantic_conf * 50) # Scaled semantic confidence score (max 50)

    if model.get("release_stage") == "stable":
        score += 30
    
    # Bonus for being the latest non-versioned alias (e.g., 'gpt-4o' over 'gpt-4o-2024-05-13')
    if model.get("is_latest", False) and model.get("version") in ["", "latest", model.get("family")]:
        score += 20

    # Penalize dated snapshots
    if model.get("release_stage") == "versioned":
        score -= 30
    
    # Penalize legacy/deprecated models significantly
    # Only penalize if status is explicitly "deprecated" OR if it matches known legacy identifiers
    is_explicitly_deprecated = model.get("status", "").lower() == "deprecated" or \
                              model.get("release_stage", "").lower() == "deprecated"
    is_known_legacy_id = any(k in model.get("model_id", "").lower() for k in ["babbage", "davinci"]) or \
                         model.get("family", "").lower() == "gpt-3.5"

    if is_explicitly_deprecated or is_known_legacy_id:
        score -= 80 # Heavy penalty for deprecated/legacy
    
    return score


# ── Step 1: Parse JSON ────────────────────────────────────────────────────────
def parse_json(path):
    """Parse discovery JSON and compute statistics from the primary source of truth."""
    with open(path) as f:
        data = json.load(f)

    all_models = []
    source_description = "normalized_models" # Default fallback
    
    # Prioritize planned_bigquery_actions.inserts + .updates
    if data.get("planned_bigquery_actions"):
        source_description = "planned_bigquery_actions.inserts + .updates"
        all_models_map = {m["model_id"]: m for m in data["planned_bigquery_actions"].get("inserts", [])}
        for m_update in data["planned_bigquery_actions"].get("updates", []):
            all_models_map[m_update["model_id"]] = m_update # Updates overwrite existing
        all_models = list(all_models_map.values())
    elif data.get("enriched_models"):
        source_description = "enriched_models"
        all_models = data.get("enriched_models", [])
    elif data.get("normalized_models"):
        source_description = "normalized_models"
        all_models = data.get("normalized_models", [])
    else:
        print("❌ ERROR: No model data found in planned_bigquery_actions, enriched_models, or normalized_models. Halting.")
        sys.exit(1)


    provider = data.get("target_provider", "openai").upper()
    run_id = data.get("run_id", datetime.now().isoformat())
    raw_source_count = len(all_models) # Capture count directly from source
    
    EXPECTED_TOTAL_MODELS = 119 # As per the request for the source of truth
    if raw_source_count != EXPECTED_TOTAL_MODELS:
        print(f"❌ ERROR: Raw source count mismatch. Expected {EXPECTED_TOTAL_MODELS} models, but parsed {raw_source_count}. Halting.")
        sys.exit(1)
    
    # No filtering allowed based on semantic confidence, enrichment availability, etc.
    # All models loaded from the source must be processed and validated.
    
    categorized_models = defaultdict(list)
    unclassified_models = []
    enriched_coverage_count = 0 # Track models with semantic enrichment data

    # Enrich each model with use_case and recommendation
    for m in all_models:
        # Ensure semantic_confidence is consistently set for models where enrichment failed but a purpose was defaulted.
        semantic_conf = m.get("semantic_confidence", 0)
        if m.get("model_purpose") and semantic_conf == 0:
            semantic_conf = 0.3 # Assign a baseline confidence if a purpose exists but semantic confidence is 0

        # All models are processed regardless of enrichment status.
        use_case = _classify_model(m)
        m["use_case"] = use_case
        
        # Check if the model has any semantic enrichment data for coverage reporting
        if semantic_conf > 0 or m.get("model_purpose"):
            enriched_coverage_count += 1

        is_latest = m.get("is_latest", False)
        is_active = m.get("is_active", True)
        
        # Determine recommendation based on new status logic.
        # DEPRECATED only if status is explicitly "deprecated" OR model_id/family is in known legacy list.
        is_explicitly_deprecated_status = m.get("status", "").lower() == "deprecated" or \
                                          m.get("release_stage", "").lower() == "deprecated"
        is_known_legacy_model = (
            "babbage" in m.get("model_id", "").lower() or
            "davinci" in m.get("model_id", "").lower() or
            "gpt-3.5" == m.get("family", "").lower() # Only gpt-3.5 family as per request, not gpt-3.5 in ID.
        )
        
        if is_explicitly_deprecated_status or is_known_legacy_model:
            rec = "[DEPRECATED]"
            color = "#da1e28"  # IBM Red
        elif semantic_conf >= 0.8 and is_latest and is_active:
            rec = "[RECOMMENDED]"
            color = "#0f62fe"  # IBM Blue
        elif semantic_conf >= 0.8 and is_active:
            rec = "[GOOD]"
            color = "#198038"  # IBM Green
        else: # Covers niche and other active models below 0.8 confidence, not explicitly deprecated
            rec = "[NICHE]"
            color = "#8a3ffc"  # IBM Purple


        m["semantic_confidence"] = semantic_conf
        m["recommendation"] = rec
        m["rec_color"] = color

        # Add model to categorized list or unclassified list
        if use_case != "Other":
            categorized_models[use_case].append(m)
        else:
            unclassified_models.append(m)
    
    # Select best model for each category using the scoring function
    best_per_usecase = {}
    for uc_key, models_in_category in categorized_models.items():
        if models_in_category:
            best_model_for_uc = max(models_in_category, key=_score_model)
            best_per_usecase[uc_key] = best_model_for_uc
            print(f"[DEBUG] Best model for '{USE_CASE_MAP_DICT.get(uc_key, {'title': uc_key})['title']}': {best_model_for_uc['model_id']} (Score: {_score_model(best_model_for_uc)})")

    if unclassified_models:
        print("\n[DEBUG] Unclassified Models:")
        for um in unclassified_models:
            print(f"  - {um.get('model_id')} (Family: {um.get('family')})")
    else:
        print("\n[DEBUG] No unclassified models.")

    # Compute confidence buckets using semantic_confidence across all parsed models
    stage_counts = defaultdict(int)
    conf_buckets = {"high": [], "medium": [], "low": []}
    for m in all_models: # Iterate through all_models to populate buckets
        stage_counts[m.get("release_stage", "unknown")] += 1
        semantic_conf = m.get("semantic_confidence", 0) # Use the potentially adjusted semantic_conf
        if semantic_conf >= 0.8:
            conf_buckets["high"].append(m)
        elif semantic_conf >= 0.5:
            conf_buckets["medium"].append(m)
        else:
            conf_buckets["low"].append(m)

    families = defaultdict(list)
    for m in all_models:
        families[m["family"]].append(m)

    return {
        "provider": provider,
        "run_id": run_id,
        "run_date": run_date,
        "source_description": source_description,
        "raw_source_count": raw_source_count, # New field for initial count
        "total": raw_source_count, # Total models processed is the raw source count
        "enriched_coverage_count": enriched_coverage_count,
        "families": dict(families),
        "family_count": len(families),
        "latest_per_family": {}, 
        "stage_counts": dict(stage_counts),
        "conf_buckets": conf_buckets,
        "all_models": all_models,
        "categorized_models": categorized_models, 
        "latest_per_usecase": best_per_usecase, 
        "unclassified_models": unclassified_models, 
    }


# ── Step 2: Generate Dashboard-Style Model Selection Guide (12-card grid) ──────
def generate_charts(stats):
    """4x3 grid of use-case cards using GridSpec."""
    from matplotlib.gridspec import GridSpec
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    categorized = stats["categorized_models"] # Use pre-classified models
    best_models_per_usecase = stats["latest_per_usecase"] # Use pre-determined best models

    BG = "#ffffff"
    CARD_BG = "#f4f4f4"
    BORDER = "#e0e0e0"
    TEXT = "#161616"
    SUBTEXT = "#525252"

    fig = plt.figure(figsize=(20, 18), facecolor=BG) # Increased figure height
    gs = GridSpec(
        nrows=5, ncols=4,
        height_ratios=[1.0, 0.7, 3.5, 3.5, 3.5], # Adjusted row heights to fit more text
        hspace=0.35, wspace=0.25,
        left=0.04, right=0.96, top=0.97, bottom=0.03
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
        _render_card(ax, uc, categorized.get(uc["key"], []), best_models_per_usecase.get(uc["key"]), CARD_BG, BORDER, TEXT, SUBTEXT)

    chart_path = f"{OUTPUT_DIR}/model_chart_{ts}.png"
    fig.savefig(chart_path, dpi=130, bbox_inches="tight", facecolor=BG, edgecolor="none")
    plt.close()
    print(f"Chart PNG: {chart_path}")
    return chart_path


def _render_card(ax, uc, models, best_model, CARD_BG, BORDER, TEXT, SUBTEXT):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    count = len(models)
    
    # Determine badge text based on the best_model's recommendation
    badge_text, badge_color = "INFO", "#525252" # Default
    if best_model:
        rec_status = best_model.get("recommendation")
        if rec_status == "[RECOMMENDED]":
            badge_text, badge_color = "RECOMMENDED", "#0f62fe"
        elif rec_status == "[GOOD]":
            badge_text, badge_color = "GOOD", "#198038"
        elif rec_status == "[NICHE]":
            badge_text, badge_color = "NICHE", "#8a3ffc"
        elif rec_status == "[DEPRECATED]":
            badge_text, badge_color = "DEPRECATED", "#da1e28"
            
    # Explicitly mark legacy/fine_tuning categories as DEPRECATED if no models or specific recommendation
    if count == 0:
        badge_text, badge_color = "EMPTY", "#a8a8a8"
    elif uc["key"] == "legacy": # Force DEPRECATED for legacy category
        badge_text, badge_color = "DEPRECATED", "#da1e28"
    elif uc["key"] == "fine_tuning" and badge_text == "INFO": # If fine-tuning and no strong recommendation
        badge_text, badge_color = "CUSTOMIZE", "#ff832b"


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

    if best_model:
        mid = best_model.get("model_id", "")
        # Truncate model_id for card display if too long
        if len(mid) > 24:
            mid_display = mid[:22] + "..."
        else:
            mid_display = mid
        
        ax.text(0.5, 7.3, "Recommended Model:", fontsize=9, color=SUBTEXT)
        ax.text(0.5, 6.7, mid_display, fontsize=11, fontweight="bold", color=TEXT, family="monospace")
        ax.text(0.5, 6.0, f"Family: {best_model.get('family', '---')}", fontsize=9, color=SUBTEXT, style="italic")
        ax.text(0.5, 5.4, f"Available: {count}", fontsize=9, color=TEXT, fontweight="bold")

        # Purpose summary
        purpose_summary = best_model.get("model_purpose", best_model.get("selection_notes", uc["desc"]))
        
        # Capability chips
        capabilities_list = best_model.get("capabilities", [])
        capability_chips = ", ".join(capabilities_list[:2]) # Show first 2 capabilities
        if len(capabilities_list) > 2:
            capability_chips += ", ..."
        
        # Combine purpose and capabilities for the text box
        desc_text = purpose_summary
        if capability_chips:
            desc_text += f"\nCapabilities: {capability_chips}"
        
        # Truncate combined description if too long
        if len(desc_text) > 180: # Heuristic for maximum displayable text in box
            desc_text = desc_text[:177] + "..."

        desc_box = mpatches.FancyBboxPatch((0.5, 0.7), 9.0, 4.0, # Made box taller
                                           boxstyle="round,pad=0.05,rounding_size=0.15",
                                           facecolor="#e8e8e8", edgecolor="none")
        ax.add_patch(desc_box)
        ax.text(5.0, 2.7, desc_text, ha="center", va="center", fontsize=8.5, color=SUBTEXT, style="italic", wrap=True)
    else:
        # If no best_model, but category is 'fine_tuning' or 'legacy', show specific message
        if uc["key"] == "legacy":
            ax.text(5.0, 5.0, "Contains older or phased-out model families.", ha="center", va="center", fontsize=10, color=SUBTEXT, style="italic")
        elif uc["key"] == "fine_tuning":
            ax.text(5.0, 5.0, "Base models for customization and fine-tuning.", ha="center", va="center", fontsize=10, color=SUBTEXT, style="italic")
        else:
            ax.text(5.0, 5.0, "No models in this category", ha="center", va="center", fontsize=10, color=SUBTEXT, style="italic")


# ── Step 3: Generate Mermaid diagram (grouped by use-case) ──────────────────────
def generate_mermaid_png(stats, validate_only=False):
    """Mindmap: category -> best model -> status. Full model names."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    categorized = stats["categorized_models"]
    best_models_per_usecase = stats["latest_per_usecase"]

    lines = [
        "%%{init: {'theme':'base','themeVariables':{'primaryColor':'#0f62fe','primaryTextColor':'#ffffff','primaryBorderColor':'#0353e9','lineColor':'#525252','fontFamily':'Helvetica'}}}%%",
        "mindmap",
        f"  root(({stats['provider']}<br/>{stats['total']} Models<br/>{stats['family_count']} Families))"
    ]
    for uc in USE_CASE_MAP:
        uc_key = uc["key"]
        models_in_category = categorized.get(uc_key, [])
        best = best_models_per_usecase.get(uc_key)

        if not best:
            continue

        count = len(models_in_category)
        
        status = best.get("recommendation", "N/A").strip("[]")

        bid = best.get("model_id", "?")
        bfam = best.get("family", "?")
        
        cat_id = uc_key.replace("_", "")
        lines.append(f"    {cat_id}[{uc['icon']} {uc['title']}<br/>({count} models)]")
        lines.append(f"      {cat_id}_model(Best: {bid})") # Use parentheses for normal nodes
        lines.append(f"      {cat_id}_fam(Family: {bfam})")
        lines.append(f"      {cat_id}_status(Status: {status})")
        
        capabilities_list = best.get("capabilities", [])
        if capabilities_list:
            caps_text = ", ".join(capabilities_list)
            # Split long capability strings into multiple lines or nodes if necessary
            # Mermaid-cli supports <br/> for line breaks in nodes
            max_cap_len = 50 # Heuristic for splitting capabilities
            current_cap_line = []
            all_cap_lines = []
            for cap in capabilities_list:
                if len(", ".join(current_cap_line + [cap])) > max_cap_len and current_cap_line:
                    all_cap_lines.append(", ".join(current_cap_line))
                    current_cap_line = [cap]
                else:
                    current_cap_line.append(cap)
            if current_cap_line:
                all_cap_lines.append(", ".join(current_cap_line))
            
            for i, line in enumerate(all_cap_lines):
                lines.append(f"      {cat_id}_caps{i}(Capabilities: {line})")


    mermaid_text = "\n".join(lines)
    mmd_path = f"{OUTPUT_DIR}/model_mindmap_{ts}.mmd"
    png_path = f"{OUTPUT_DIR}/model_mindmap_{ts}.png"
    with open(mmd_path, "w") as f:
        f.write(mermaid_text)
    print(f"\n=== MERMAID PREVIEW ===\n{mermaid_text}\n=====================\n")

    if validate_only:
        print(f"[VALIDATE-ONLY] Skipping Mermaid PNG generation.")
        return png_path, mmd_path
        
    ret = os.system(
        f"npx --yes @mermaid-js/mermaid-cli mmdc -i {mmd_path} -o {png_path} -t default -b white -w 3000 -H 2000 --scale 2 2>/dev/null"
    )
    if ret != 0 or not os.path.exists(png_path) or os.path.getsize(png_path) == 0:
        print("WARNING: mermaid-cli failed or produced empty file, using matplotlib fallback")
        png_path = _matplotlib_mindmap_fallback(stats, categorized, best_models_per_usecase, ts)
    print(f"Mindmap: {png_path}")
    return png_path, mmd_path


def _matplotlib_mindmap_fallback(stats, categorized, best_models_per_usecase, ts):
    import math
    fig, ax = plt.subplots(figsize=(24, 18), facecolor="#ffffff")
    ax.set_xlim(-15, 15)
    ax.set_ylim(-12, 12)
    ax.axis("off")
    ax.set_aspect("equal")

    center = mpatches.Circle((0, 0), 2.2, facecolor="#0f62fe", edgecolor="none")
    ax.add_patch(center)
    ax.text(0, 0.5, stats["provider"], ha="center", va="center", fontsize=16, fontweight="bold", color="#ffffff")
    ax.text(0, 0, f"{stats['total']} Models", ha="center", va="center", fontsize=12, color="#ffffff")
    ax.text(0, -0.4, f"{stats['family_count']} Families", ha="center", va="center", fontsize=12, color="#ffffff")

    active_use_cases = [uc for uc in USE_CASE_MAP if categorized.get(uc["key"])]
    n = len(active_use_cases)
    
    radius = 9
    for i, uc in enumerate(active_use_cases):
        angle = (2 * math.pi * i / n) - math.pi / 2
        cx = radius * math.cos(angle)
        cy = radius * math.sin(angle)
        
        best = best_models_per_usecase.get(uc["key"])

        ax.plot([0, cx * 0.2], [0, cy * 0.2], color=uc["color"], linewidth=2, alpha=0.6, zorder=0)

        bubble = mpatches.FancyBboxPatch((cx - 2.8, cy - 1.2), 5.6, 2.4,
                                         boxstyle="round,pad=0.1,rounding_size=0.3",
                                         facecolor=uc["color"], edgecolor="none", zorder=1)
        ax.add_patch(bubble)
        ax.text(cx, cy + 0.6, f"{uc['icon']} {uc['title']}", ha="center", va="center", fontsize=12, fontweight="bold", color="#ffffff")
        
        if best:
            model_id_display = best.get("model_id", "?")
            
            # Simple word wrap for model_id in matplotlib fallback
            wrapped_model_id = ""
            current_line = []
            for word in model_id_display.split('-'): # Split by common model_id separator
                if len('-'.join(current_line + [word])) <= 20: # Keep line length reasonable
                    current_line.append(word)
                else:
                    wrapped_model_id += '-'.join(current_line) + '\n'
                    current_line = [word]
            if current_line:
                wrapped_model_id += '-'.join(current_line)
            
            ax.text(cx, cy - 0.2, f"Best: {wrapped_model_id}", ha="center", va="center", fontsize=9, color="#ffffff", wrap=True)

    path = f"{OUTPUT_DIR}/model_mindmap_matplotlib_{ts}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="#ffffff")
    plt.close()
    return path


# ── Step 3.5: Verify no hallucination (number consistency) ──────────────────────
# ── Step 3.5: Build Visual Context ───────────────────────────────────────────
def build_visual_context(stats):
    """Extracts and structures relevant data for visual prompt generation."""
    context = {
        "provider": stats['provider'],
        "total_models": stats['total'],
        "family_count": stats['family_count'],
        "high_confidence_count": len(stats['conf_buckets']['high']),
        "categories": [],
        "family_distribution": {}
    }

    # Top families by count
    family_counts = defaultdict(int)
    for model in stats["all_models"]:
        family_counts[model.get("family", "unknown")] += 1
    
    sorted_families = sorted(family_counts.items(), key=lambda item: item[1], reverse=True)
    context["family_distribution"] = {f: c for f, c in sorted_families[:5]} # Top 5 families

    # Categories with best model and counts
    for uc_key, uc_data in USE_CASE_MAP_DICT.items():
        models_in_category = stats["categorized_models"].get(uc_key, [])
        best_model = stats["latest_per_usecase"].get(uc_key)
        
        category_info = {
            "key": uc_key,
            "title": uc_data["title"],
            "count": len(models_in_category),
            "best_model_id": best_model.get("model_id", "N/A") if best_model else "N/A",
            "best_model_family": best_model.get("family", "N/A") if best_model else "N/A",
            "purpose_summary": best_model.get("model_purpose", uc_data["desc"]) if best_model else uc_data["desc"],
            "capabilities": best_model.get("capabilities", []) if best_model else []
        }
        context["categories"].append(category_info)
    
    return context


# ── Step 3.6: Generate Imagen Prompts ────────────────────────────────────────
def generate_visual_prompts(context):
    """Generates detailed prompts for Vertex AI Imagen based on extracted context."""
    provider = context["provider"]
    total_models = context["total_models"]
    family_count = context["family_count"]
    high_conf_count = context["high_confidence_count"]
    
    # Dashboard Prompt
    dashboard_cards_prompt = []
    for category in context["categories"]:
        if category["count"] > 0:
            caps_str = ", ".join(category["capabilities"][:2])
            card_line = f"  - Card for '{category['title']}': Best model '{category['best_model_id']}' ({category['best_model_family']} family), {category['count']} models. Capabilities: {caps_str}."
            dashboard_cards_prompt.append(card_line)
    
    top_families_str = ", ".join([f"{fam} ({count})" for fam, count in context["family_distribution"].items()])

    dashboard_prompt = f"""
Create a visually striking enterprise SaaS dashboard, designed for executives, titled "{provider} Model Discovery Intelligence".
The dashboard should present data clearly, using a professional, clean, dark navy and white theme. Avoid any fake charts or numbers.
The layout should be clean and structured, suitable for a 16:9 aspect ratio (LinkedIn-ready).

Key metrics to display prominently at the top:
- Total Models: {total_models}
- Model Families: {family_count}
- High Confidence Models: {high_conf_count}

The dashboard must include individual, well-designed cards for the following model selection categories. Each card should clearly show the category title, the best recommended model for that category (model ID and family), and the total count of available models in that category. Incorporate capability chips within each card if possible.

Categories and their details:
{chr(10).join(dashboard_cards_prompt)}

Ensure text is large, readable, and avoids any emojis or unnecessary clutter. The overall aesthetic should communicate data-driven insights with elegance.
"""

    # Mindmap Prompt
    mindmap_branches_prompt = []
    for category in context["categories"]:
        if category["count"] > 0:
            caps_str = ", ".join(category["capabilities"][:3]) # More capabilities for mindmap
            branch_line = f"  - Branch for '{category['title']}' ({category['count']} models): Best model '{category['best_model_id']}' (Family: {category['best_model_family']}). Key capabilities: {caps_str}."
            mindmap_branches_prompt.append(branch_line)

    mindmap_prompt = f"""
Design a clean, professional cloud architecture style mindmap or hierarchical diagram, representing an "{provider} Model Registry" for an enterprise. The visual should be suitable for LinkedIn (16:9 aspect ratio) and have readable text.

The central node of the mindmap should be "{provider} Model Registry".

The mindmap should clearly illustrate the architecture and data flow:
1.  **Official API** (Source of Truth for Model Discovery, e.g., {provider}'s /v1/models endpoint)
2.  **LangGraph Discovery Agent** (Automated process for model discovery)
3.  **Gemini Enrichment Engine** (Semantic analysis and confidence scoring)
4.  **BigQuery Registry** (Centralized data storage for all discovered models)
5.  **Publishing Assets** (Outputs like dashboards, mindmaps, reports)

Main branches extending from the central "{provider} Model Registry" node should represent key model use-case categories. For each category branch, display the category title, the number of models in that category, the best recommended model (model ID and family), and its key capabilities.

Categories and their details:
{chr(10).join(mindmap_branches_prompt)}

Highlight the architecture flow visually. Ensure no hallucinated model names or numbers are present, only factual counts from the data. Avoid emojis. The style should be modern, clean, and enterprise-grade.
"""

    return dashboard_prompt, mindmap_prompt


# ── Step 3.7: Call Vertex AI Imagen ──────────────────────────────────────────
def call_vertex_imagen(prompt: str, output_path: str, gcp_project: str, gcp_location: str, imagen_model: str):
    """
    Calls Google Cloud Vertex AI Imagen to generate an image from a prompt.
    Saves the generated image to output_path.
    """
    if not _HAS_VERTEX_AI:
        print(f"❌ Vertex AI libraries not installed. Skipping Imagen generation for: {output_path}")
        return None

    try:
        print(f"Calling Vertex AI Imagen for {output_path} with model: {imagen_model}...")
        vertexai.init(project=gcp_project, location=gcp_location)
        
        # Initialize the ImageGenerationModel correctly
        model = ImageGenerationModel.from_pretrained(imagen_model)
        
        images = model.generate_images(
            prompt=prompt,
            number_of_images=1, # Request only one image
            aspect_ratio="16:9" # As per requirement
        )

        if images and images.images: # Check if images were returned
            image_bytes = images.images[0]._image_bytes
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            print(f"✅ Imagen generated: {output_path}")
            return output_path
        else:
            print(f"⚠️ Imagen generation failed for {output_path}. No image candidates returned.")
            # Imagen API response structure for errors might vary, log more detail if available
            if hasattr(images, 'error') and images.error:
                print(f"   Error details: {images.error}")
            return None
    except Exception as e:
        print(f"❌ Error calling Vertex AI Imagen for {output_path}: {e}")
        return None


# ── Step 3.8: Verify no hallucination (number consistency) ──────────────────────
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
def update_readme(stats, li_url, med_url, dashboard_img_path, mindmap_img_path):
    """Update README.md with latest run badge and image links."""
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
| Dashboard Visual | {dashboard_img_path or 'N/A'} |
| Mindmap Visual | {mindmap_img_path or 'N/A'} |

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
    validate_only = "--validate-only" in sys.argv
    generate_image_prompts_only = "--generate-image-prompts" in sys.argv
    use_vertex_imagen = "--use-vertex-imagen" in sys.argv
    
    # Parse specific CLI arguments for Vertex AI
    imagen_model_arg = None
    gcp_project_arg = None
    gcp_location_arg = None
    for i, arg in enumerate(sys.argv):
        if arg == "--imagen-model" and i + 1 < len(sys.argv):
            imagen_model_arg = sys.argv[i+1]
        elif arg == "--gcp-project" and i + 1 < len(sys.argv):
            gcp_project_arg = sys.argv[i+1]
        elif arg == "--gcp-location" and i + 1 < len(sys.argv):
            gcp_location_arg = sys.argv[i+1]

    # Default to env vars if not provided via CLI, or use hardcoded defaults
    current_gcp_project = gcp_project_arg or GCP_PROJECT
    current_gcp_location = gcp_location_arg or GCP_LOCATION
    current_imagen_model = imagen_model_arg or IMAGEN_MODEL

    # Determine json_path, skipping all flags
    json_path_args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    # Also skip potential values for flags, e.g., 'ctoteam' after '--gcp-project'
    cleaned_json_path_args = []
    skip_next = False
    for arg in sys.argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if arg.startswith("--"):
            if arg in ["--imagen-model", "--gcp-project", "--gcp-location"]:
                skip_next = True # Value for this flag will be next
            continue
        cleaned_json_path_args.append(arg)
    
    json_path = cleaned_json_path_args[0] if cleaned_json_path_args else "agents/model_discovery_candidates_openai.json"


    print(f"\n{'='*60}")
    print(f"  DISCOVERY PUBLISHER")
    print(f"  Input: {json_path}")
    print(f"  Validate Only: {validate_only}")
    print(f"  Generate Image Prompts: {generate_image_prompts_only}")
    print(f"  Use Vertex Imagen: {use_vertex_imagen}")
    if use_vertex_imagen:
        print(f"    GCP Project: {current_gcp_project}")
        print(f"    GCP Location: {current_gcp_location}")
        print(f"    Imagen Model: {current_imagen_model}")
    print(f"{'='*60}\n")

    print("📦 Parsing JSON and classifying models...")
    stats = parse_json(json_path)
    print(f"   Source used: {stats['source_description']}") # Access from stats
    print(f"   Total parsed: {stats['total']} models")
    print(f"   Enriched coverage: {stats['enriched_coverage_count']}/{stats['total']} models\n")

    # Print summary statistics
    high = len(stats['conf_buckets']['high'])
    medium = len(stats['conf_buckets']['medium'])
    low = len(stats['conf_buckets']['low'])
    print(f"\n{'='*60}")
    print(f"SUMMARY STATISTICS")
    print(f"{'='*60}")
    print(f"✅ High Confidence (>=0.8): {high} models")
    print(f"⚠️  Medium Confidence (0.5-0.8): {medium} models")
    print(f"❌ Low Confidence (<0.5): {low} models")
    print(f"{'='*60}\n")
    
    print("\nCategory Counts:")
    for uc_key, uc_data in USE_CASE_MAP_DICT.items():
        count = len(stats["categorized_models"].get(uc_key, []))
        best_model_info = stats["latest_per_usecase"].get(uc_key)
        best_model_str = f"Best: {best_model_info['model_id']} (Score: {_score_model(best_model_info)})" if best_model_info else "N/A"
        print(f"  - {uc_data['title']}: {count} models ({best_model_str})")
    
    if stats["unclassified_models"]:
        print(f"\n[UNCLASSIFIED] {len(stats['unclassified_models'])} models were not classified:")
        for um in stats["unclassified_models"]:
            print(f"  - {um.get('model_id')} (Family: {um.get('family')})")
    else:
        print("\n[DEBUG] No unclassified models.")

    print(f"\nRAW SOURCE COUNT: {stats['raw_source_count']}")
    print(f"PARSED COUNT: {stats['total']}")
    print(f"ENRICHED COVERAGE: {stats['enriched_coverage_count']}/{stats['total']} models\n")

    # Print summary statistics
    high = len(stats['conf_buckets']['high'])
    medium = len(stats['conf_buckets']['medium'])
    low = len(stats['conf_buckets']['low'])
    print(f"\n{'='*60}")
    print(f"SUMMARY STATISTICS")
    print(f"{'='*60}")
    print(f"✅ High Confidence (>=0.8): {high} models")
    print(f"⚠️  Medium Confidence (0.5-0.8): {medium} models")
    print(f"❌ Low Confidence (<0.5): {low} models")
    print(f"{'='*60}\n")
    
    print("\nCategory Counts:")
    for uc_key, uc_data in USE_CASE_MAP_DICT.items():
        count = len(stats["categorized_models"].get(uc_key, []))
        best_model_info = stats["latest_per_usecase"].get(uc_key)
        # Use only model_id and score for best_model_str
        best_model_str = f"Best: {best_model_info['model_id']} (Score: {_score_model(best_model_info)})" if best_model_info else "N/A"
        print(f"  - {uc_data['title']}: {count} models ({best_model_str})")
    
    if stats["unclassified_models"]:
        print(f"\n[UNCLASSIFIED] {len(stats['unclassified_models'])} models were not classified:")
        for um in stats["unclassified_models"]:
            print(f"  - {um.get('model_id')} (Family: {um.get('family')})")
    else:
        print("\n[DEBUG] No unclassified models.")

    print(f"\n{'='*60}\n")

    # Build visual context before potentially exiting for validate_only
    visual_context = build_visual_context(stats)

    if validate_only:
        print("\n✅ Validation complete. Exiting (--validate-only flag used).")
        return

    dashboard_img_path = None
    mindmap_img_path = None
    
    # Generate image prompts
    dashboard_prompt, mindmap_prompt = generate_visual_prompts(visual_context)
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dashboard_prompt_path = f"{OUTPUT_DIR}/dashboard_image_prompt_{ts}.txt"
    mindmap_prompt_path = f"{OUTPUT_DIR}/mindmap_image_prompt_{ts}.txt"

    with open(dashboard_prompt_path, "w") as f:
        f.write(dashboard_prompt)
    with open(mindmap_prompt_path, "w") as f:
        f.write(mindmap_prompt)
    print(f"\n✅ Dashboard Image Prompt saved: {dashboard_prompt_path}")
    print(f"✅ Mindmap Image Prompt saved: {mindmap_prompt_path}")

    # Optionally call Vertex AI Imagen
    if use_vertex_imagen:
        if _HAS_VERTEX_AI:
            # Pass CLI arguments to the Imagen call
            dashboard_img_path = call_vertex_imagen(
                dashboard_prompt, 
                f"{OUTPUT_DIR}/dashboard_vertex_{ts}.png",
                current_gcp_project, # Use current_gcp_project
                current_gcp_location, # Use current_gcp_location
                current_imagen_model # Use current_imagen_model
            )
            mindmap_img_path = call_vertex_imagen(
                mindmap_prompt, 
                f"{OUTPUT_DIR}/mindmap_vertex_{ts}.png",
                current_gcp_project, # Use current_gcp_project
                current_gcp_location, # Use current_gcp_location
                current_imagen_model # Use current_imagen_model
            )
        else:
            print("⚠️ Skipping Vertex AI Imagen call because libraries are not installed.")

    if generate_image_prompts_only and not use_vertex_imagen:
        print("\n✅ Image prompt generation complete. Exiting (--generate-image-prompts flag used, no --use-vertex-imagen).")
        return

    # Fallback to matplotlib if Imagen not used or failed
    if not dashboard_img_path:
        print("\n📊 Generating Matplotlib Dashboard chart (fallback)...")
        chart_png = generate_charts(stats)
        dashboard_img_path = chart_png
    else:
        print(f"\nSkipping Matplotlib Dashboard (Vertex Imagen used: {dashboard_img_path})")

    if not mindmap_img_path:
        print("\n🗺  Generating Mermaid/Matplotlib Mindmap (fallback)...")
        diagram_png, diagram_mmd = generate_mermaid_png(stats, validate_only)
        mindmap_img_path = diagram_png
    else:
        print(f"\nSkipping Mermaid/Matplotlib Mindmap (Vertex Imagen used: {mindmap_img_path})")


    if not publish_mode:
        print("\n⏸  Visual generation complete. Publish steps skipped (use --publish to enable posting).")
        print(f"📊 Dashboard Image: {dashboard_img_path}")
        print(f"🗺  Mindmap Image:   {mindmap_img_path}")
        print(f"📝 Dashboard Prompt: {dashboard_prompt_path}")
        print(f"📝 Mindmap Prompt:   {mindmap_prompt_path}")
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
    # Use the dashboard_img_path (which could be Imagen or Matplotlib) for LinkedIn
    li_url = post_linkedin(linkedin_text, dashboard_img_path)

    print("\n📝 Posting to Medium...")
    title = f"{stats['provider']} Has {stats['total']} Active AI Models -- Full Discovery Report {stats['run_date']}"
    med_url = post_medium(medium_content, title) # Medium doesn't directly support image upload in API, so the image is referenced in the text

    print("\n📖 Updating README...")
    update_readme(stats, li_url, med_url, dashboard_img_path, mindmap_img_path) # Pass image paths to README update

    print(f"\n{'='*60}")
    print("  PUBLISH COMPLETE")
    print(f"{'='*60}")
    print(f"📊 Dashboard Image: {dashboard_img_path}")
    print(f"🗺  Mindmap Image:   {mindmap_img_path}")
    print(f"📝 LinkedIn:        {li_url or li_path}")
    print(f"📄 Medium:          {med_url or med_path_local}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
