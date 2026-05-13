"""
visual_design_agents.py

Multi-agent visual design pipeline:
1. Visual Planning Agent (gemini-2.5-pro) → design spec
2. UX Design Critic Agent (gemini-2.5-pro) → validate spec
3. Prompt QA Agent (gemini-2.5-flash) → safe, validated prompt
4. Image Quality Review Agent (gemini-2.5-flash) → check generated image
"""

import json
import os
import requests
from typing import Dict, Any, Optional, List

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def _call_gemini_text(prompt: str, model_name: str, max_tokens: int, temperature: float, top_p: float) -> str:
    """Call Gemini API and return text response."""
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
        headers={"x-goog-api-key": GOOGLE_API_KEY},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
                "topP": top_p,
            },
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if "candidates" not in data or not data["candidates"]:
        raise ValueError(f"Invalid Gemini response: {data}")
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Failed to extract text from Gemini response: {data}. Error: {e}")


def build_visual_design_spec(stats: Dict[str, Any], style: str = "ibm-carbon") -> Dict[str, Any]:
    """
    Visual Planning Agent: Convert structured JSON model data into a design specification.
    Uses gemini-2.5-pro for high-quality design intent, falls back to gemini-2.5-flash.

    Returns JSON spec with layout, sections, hierarchy, and visual rules.
    """
    if not GOOGLE_API_KEY:
        return {"error": "GOOGLE_API_KEY not set", "spec": None, "approved": False, "warnings": ["GOOGLE_API_KEY not set"]}

    provider = stats.get("provider", "OpenAI")
    total = stats.get("total", 0)
    family_count = stats.get("family_count", 0)
    high_conf = len(stats.get("conf_buckets", {}).get("high", []))

    categories_summary = []
    for uc_key, models in stats.get("categorized_models", {}).items():
        best = None
        if stats.get("latest_per_usecase", {}).get(uc_key):
            best = stats["latest_per_usecase"][uc_key]
        categories_summary.append({
            "key": uc_key,
            "count": len(models),
            "best_model": best.get("model_id") if best else "N/A"
        })

    prompt = f"""You are a senior enterprise UX design architect specialized in SaaS dashboards.

Your task: Convert raw AI model metadata into a clean, factual design specification for an IBM Carbon-style enterprise dashboard.

Context:
- Provider: {provider}
- Total models: {total}
- Model families: {family_count}
- High-confidence models: {high_conf}
- Categories: {json.dumps(categories_summary[:8], indent=2)}
- Style: IBM Carbon enterprise (light theme, clean grid, readable typography)

Design Requirements:
- Light background (white / #f4f4f4)
- IBM blue accents (#0f62fe)
- Grid layout: header row + KPI metrics row + category cards (4x3 or similar)
- Top KPI section: total models, families, high-confidence count, (optional: run date)
- Main content: category cards showing:
  * Category title and icon
  * Model count in category
  * Best recommended model (title + family)
  * One-line purpose summary
  * Status badge (RECOMMENDED / GOOD / NICHE / DEPRECATED)
- No dark mode
- No fake text or lorem ipsum
- No dense tables or tiny labels
- Ample whitespace
- Professional SaaS aesthetic
- LinkedIn-ready 16:9 aspect ratio
- Actual data only (no placeholder numbers)

Output JSON specification with:
{{
  "design_type": "enterprise_dashboard",
  "aspect_ratio": "16:9",
  "background": "#ffffff",
  "accent_color": "#0f62fe",
  "sections": [
    {{
      "name": "header",
      "type": "banner",
      "background": "#0f62fe",
      "height_ratio": 0.12,
      "content": "title + provider name"
    }},
    {{
      "name": "kpi_metrics",
      "type": "metrics_row",
      "height_ratio": 0.15,
      "metrics": ["total_models", "families", "high_confidence", "discovery_date"]
    }},
    {{
      "name": "category_cards",
      "type": "grid",
      "grid_layout": "4 columns, 3 rows",
      "height_ratio": 0.73,
      "card_content": ["title", "icon", "model_count", "best_model_id", "family", "purpose", "status_badge"],
      "card_background": "#f4f4f4",
      "card_border": "#e0e0e0"
    }}
  ],
  "constraints": [
    "NO dark mode",
    "NO fake text or UI",
    "Real data: {total} models, {family_count} families, {high_conf} high-confidence"
  ]
}}"""

    try:
        # Try gemini-2.5-pro first, then fall back to flash
        for model in ["gemini-2.5-pro", "gemini-2.5-flash"]:
            try:
                spec_text = _call_gemini_text(prompt, model, 2000, 0.2, 0.8)
                spec = json.loads(spec_text)
                return {"approved": True, "spec": spec, "warnings": []}
            except Exception as e:
                if model == "gemini-2.5-pro":
                    continue  # Try flash
                raise

    except Exception as e:
        return {"approved": False, "spec": None, "warnings": [f"Design spec generation failed: {e}"]}


def critique_visual_spec(spec: Dict[str, Any], stats: Dict[str, Any], style: str = "ibm-carbon") -> Dict[str, Any]:
    """
    UX Design Critic Agent: Review and refine design spec.
    Uses gemini-2.5-pro for expert critique.

    Returns: approved (bool), optimized_spec, suggestions, warnings.
    """
    if not GOOGLE_API_KEY:
        return {"approved": False, "spec": spec, "warnings": ["GOOGLE_API_KEY not set"]}

    total = stats.get("total", 0)
    family_count = stats.get("family_count", 0)
    high_conf = len(stats.get("conf_buckets", {}).get("high", []))

    prompt = f"""You are a senior UX/design critique expert. Review this dashboard design spec for quality, clarity, and adherence to IBM Carbon guidelines.

Design Spec:
{json.dumps(spec, indent=2)}

Validation Checklist:
1. ✓ No dark mode? (must be light theme)
2. ✓ No fake text or lorem ipsum?
3. ✓ All metric values are exact? (must show {total} models, {family_count} families, {high_conf} high-confidence)
4. ✓ Card layout allows clear reading of model names?
5. ✓ Spacing/whitespace adequate?
6. ✓ Typography hierarchy clear?
7. ✓ No overcrowding?
8. ✓ Status badges distinct and appropriate?
9. ✓ Grid dimensions feasible (cards don't overlap)?
10. ✓ Alignment consistent?

Return JSON:
{{
  "approved": true/false,
  "issues": ["issue1", "issue2", ...],
  "suggestions": ["suggestion1", ...],
  "optimizations": {{
    "spacing": "...",
    "typography": "...",
    "layout": "..."
  }},
  "final_spec": {{ ... (complete spec or None) }}
}}

Be strict about:
- Rejecting dark themes
- Rejecting overcrowded layouts
- Rejecting fake/placeholder text
- Requiring exact fact accuracy
- Requiring adequate whitespace

Be lenient about:
- Minor color adjustments
- Font size tweaks
- Icon styles"""

    try:
        review_text = _call_gemini_text(prompt, "gemini-2.5-pro", 2000, 0.2, 0.8)
        review = json.loads(review_text)
        return {
            "approved": bool(review.get("approved", False)),
            "spec": review.get("final_spec") or spec,
            "issues": review.get("issues", []),
            "suggestions": review.get("suggestions", []),
            "optimizations": review.get("optimizations", {}),
            "warnings": []
        }
    except Exception as e:
        return {
            "approved": False,
            "spec": spec,
            "issues": [str(e)],
            "suggestions": [],
            "optimizations": {},
            "warnings": [f"Critique failed: {e}"]
        }


def compose_imagen_prompt_from_spec(spec: Dict[str, Any], stats: Dict[str, Any], style: str = "ibm-carbon") -> str:
    """
    Compose an Imagen prompt from the validated design spec.
    Ensures all critical constraints are included.

    Returns: final_prompt string ready for Imagen.
    """
    provider = stats.get("provider", "OpenAI")
    total = stats.get("total", 0)
    family_count = stats.get("family_count", 0)
    high_conf = len(stats.get("conf_buckets", {}).get("high", []))

    constraints = spec.get("constraints", [])
    constraint_text = " ".join(constraints)

    prompt = f"""Create a premium enterprise analytics dashboard visual for {provider} AI Model Registry.

Style: IBM Carbon light theme
- White background with light gray cards (#f4f4f4)
- IBM blue accents (#0f62fe)
- Clean grid layout
- Professional SaaS aesthetic
- 16:9 aspect ratio
- LinkedIn publication quality

Data to Display:
- Provider: {provider}
- Total Models: {total}
- Model Families: {family_count}
- High-Confidence (Production-Ready): {high_conf}

Layout:
1. Header Banner: "{provider} AI Model Discovery Dashboard" (large, centered, white text on blue)
2. KPI Row: 4 large metric cards showing: {total} Total Models | {family_count} Families | {high_conf} High-Confidence | (Optional: Today's Date)
3. Main Grid: Category cards in 4x3 layout, each card shows:
   - Category title (bold, white text on category color bar at top)
   - Model count in category
   - Best recommended model name (monospace, large readable text)
   - Model family
   - One-line purpose or capability summary
   - Status badge (RECOMMENDED = blue, GOOD = green, NICHE = purple, DEPRECATED = red)

Visual Rules:
- NO dark mode
- NO fake text or placeholder UI
- NO tiny labels (all text at least 9pt)
- NO dense tables
- NO paragraphs
- NO misspellings
- NO duplicate or overlapping cards
- NO abstract or cinematic visuals
- NO clutter
- Ample whitespace between elements
- Professional typography hierarchy
- Clean borders and shadows (subtle, soft)
- Consistent alignment on a grid

Strict Constraints:
{constraint_text}

Generate a polished, enterprise-grade dashboard visual that could be published on LinkedIn. Focus on clarity, readability, and accurate data representation."""

    return prompt


def review_imagen_prompt_qa(prompt: str, stats: Dict[str, Any], image_type: str = "dashboard") -> Dict[str, Any]:
    """
    Prompt QA Agent: Validate Imagen prompt for safety, factual accuracy, and compliance.
    Uses gemini-2.5-flash for fast review.

    Returns: approved (bool), final_prompt, warnings, must_include, must_avoid.
    """
    if not GOOGLE_API_KEY:
        return {
            "approved": False,
            "final_prompt": "",
            "warnings": ["GOOGLE_API_KEY not set"],
            "must_include": [],
            "must_avoid": []
        }

    total = stats.get("total", 0)
    family_count = stats.get("family_count", 0)
    high_conf = len(stats.get("conf_buckets", {}).get("high", []))

    qa_prompt = f"""You are a prompt QA expert for image generation. Validate this Imagen prompt.

Imagen Prompt:
{prompt}

Fact Check (REQUIRED):
- Provider mentions: must include "{stats.get('provider', 'OpenAI')}"
- Total models: must mention "{total}" OR "total models: {total}"
- Families: must mention "{family_count}" families
- High-confidence: must mention "{high_conf}" high-confidence
- Aspect ratio: must specify "16:9"

Safety Checks:
- No request for "exact BI table" or "spreadsheet"
- No request for dense text or tiny labels
- No request for dark theme
- No fake/placeholder text
- No cinematic hero visual (must be dashboard)
- No abstract cloud art
- Specify IBM Carbon / light theme explicitly

Return JSON:
{{
  "approved": true/false,
  "fact_check_passed": true/false,
  "safety_check_passed": true/false,
  "final_prompt": "...(refined prompt or original)",
  "warnings": ["..."],
  "must_include": ["..."],
  "must_avoid": ["..."],
  "fixes_applied": ["..."]
}}

If fact check fails, reject immediately.
If safety check fails, suggest specific fixes."""

    try:
        review_text = _call_gemini_text(qa_prompt, "gemini-2.5-flash", 1500, 0.2, 0.8)
        review = json.loads(review_text)

        fact_ok = review.get("fact_check_passed", False)
        safety_ok = review.get("safety_check_passed", False)
        approved = fact_ok and safety_ok

        return {
            "approved": approved,
            "final_prompt": review.get("final_prompt", prompt),
            "warnings": review.get("warnings", []),
            "must_include": review.get("must_include", []),
            "must_avoid": review.get("must_avoid", []),
            "fact_check_passed": fact_ok,
            "safety_check_passed": safety_ok,
        }
    except Exception as e:
        return {
            "approved": False,
            "final_prompt": prompt,
            "warnings": [f"QA review failed: {e}"],
            "must_include": [],
            "must_avoid": [],
            "fact_check_passed": False,
            "safety_check_passed": False,
        }


def validate_image_matches_request(extracted_text: str, stats: Dict[str, Any], image_type: str = "dashboard") -> Dict[str, Any]:
    """
    Validate that extracted image text matches what was requested in the prompt.

    Checks:
    - Provider name present
    - Model count exact match
    - Family count exact match
    - High-confidence count present
    - For dashboard: categories visible
    - For architecture: pipeline components visible

    Returns: match_score (0-100), missing_items, confidence.
    """
    text_lower = extracted_text.lower()
    provider = stats.get("provider", "OpenAI").lower()
    total = str(stats.get("total", 0))
    families = str(stats.get("family_count", 0))
    high_conf = str(len(stats.get("conf_buckets", {}).get("high", [])))

    missing = []
    score = 100

    # 1. Provider check
    if provider not in text_lower:
        missing.append(f"Provider '{stats.get('provider', 'OpenAI')}' missing")
        score -= 25

    # 2. Total models check
    if total not in extracted_text:
        missing.append(f"Total count '{total}' missing")
        score -= 25

    # 3. Families check
    if families not in extracted_text:
        missing.append(f"Family count '{families}' missing")
        score -= 20

    # 4. High-confidence check
    if high_conf not in extracted_text:
        missing.append(f"High-confidence count '{high_conf}' missing")
        score -= 15

    # 5. Image-type specific checks
    if image_type == "dashboard":
        # Dashboard should show categories
        categories = ["complex reasoning", "image generation", "chat", "embeddings"]
        found = sum(1 for cat in categories if cat in text_lower)
        if found < 2:
            missing.append(f"Only {found} categories found (expected ≥2)")
            score -= 15
    elif image_type == "architecture":
        # Architecture should show pipeline
        pipeline_steps = ["official api", "langraph", "gemini", "bigquery", "registry"]
        found = sum(1 for step in pipeline_steps if step in text_lower)
        if found < 3:
            missing.append(f"Only {found} pipeline steps found (expected ≥3)")
            score -= 20

    return {
        "matches_request": score >= 70,
        "match_score": max(0, score),
        "missing_items": missing,
        "confidence": "HIGH" if score >= 90 else "MEDIUM" if score >= 70 else "LOW"
    }


def review_generated_image(image_path: str, stats: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Image Quality Review Agent: Analyze generated image using Gemini vision.
    Checks for: spelling errors, text corruption, alignment, duplicates, readability.

    Returns: approved (bool), issues, extracted_text, quality_score.
    """
    if not os.path.exists(image_path):
        return {
            "approved": False,
            "issues": [f"Image not found: {image_path}"],
            "extracted_text": "",
            "quality_score": 0,
            "needs_retry": True
        }

    if not GOOGLE_API_KEY:
        return {
            "approved": True,
            "issues": ["GOOGLE_API_KEY not set - skipping vision review"],
            "extracted_text": "",
            "quality_score": -1,
            "needs_retry": False
        }

    try:
        extracted_text = _extract_image_text(image_path)
        quality_check = _analyze_image_quality(extracted_text, stats)

        # Determine image type from context
        image_type = "dashboard" if "dashboard" in image_path.lower() else "architecture"

        # Validate that image matches request
        match_check = validate_image_matches_request(extracted_text, stats, image_type=image_type)

        # Combine checks
        all_approved = quality_check.get("approved", False) and match_check.get("matches_request", False)
        all_issues = quality_check.get("issues", []) + match_check.get("missing_items", [])

        return {
            "approved": all_approved,
            "quality_approved": quality_check.get("approved", False),
            "matches_request": match_check.get("matches_request", False),
            "issues": all_issues,
            "quality_issues": quality_check.get("issues", []),
            "missing_items": match_check.get("missing_items", []),
            "extracted_text": extracted_text,
            "quality_score": quality_check.get("score", 0),
            "match_score": match_check.get("match_score", 0),
            "confidence": match_check.get("confidence", "LOW"),
            "needs_retry": len(all_issues) > 0,
            "suggestions": quality_check.get("suggestions", []),
            "image_type": image_type
        }
    except Exception as e:
        return {
            "approved": False,
            "quality_approved": False,
            "matches_request": False,
            "issues": [f"Image review failed: {e}"],
            "extracted_text": "",
            "quality_score": 0,
            "match_score": 0,
            "confidence": "LOW",
            "needs_retry": False
        }


def _extract_image_text(image_path: str) -> str:
    """
    Extract text from image using Gemini vision API.

    Returns: Extracted text from image.
    """
    import base64

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    prompt = """Extract ALL text visible in this image.
List every word, number, label, and text element exactly as it appears.
Include: headers, card titles, metrics, numbers, badges, category names, model names.
Return a clean list of all text found, line by line."""

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": GOOGLE_API_KEY},
        json={
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": image_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 2000,
                "temperature": 0.2,
                "topP": 0.8,
            },
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if "candidates" not in data or not data["candidates"]:
        raise ValueError(f"Invalid Gemini vision response: {data}")

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Failed to extract text from Gemini vision response: {data}. Error: {e}")


def _refine_prompt_from_issues(original_prompt: str, review: Dict[str, Any]) -> str:
    """
    Refine Imagen prompt based on detected issues.

    Adjusts prompt if:
    - Text is duplicated → add "no duplicate text"
    - Spelling issues → add "spell all text correctly"
    - Missing items → add specific requirement
    """
    issues = review.get("issues", [])
    refined = original_prompt

    # Add constraints based on issues
    if any("duplicate" in i.lower() for i in issues):
        if "no duplicate" not in refined.lower():
            refined += " | CRITICAL: Ensure NO duplicate text or labels."

    if any("spell" in i.lower() or "corruption" in i.lower() for i in issues):
        if "spell" not in refined.lower():
            refined += " | CRITICAL: Spell every word correctly, no garbled text."

    missing = review.get("missing_items", [])
    if any("categor" in m.lower() for m in missing):
        refined += " | CRITICAL: Show ALL model categories clearly and separately."

    if any("pipeline" in m.lower() for m in missing):
        refined += " | CRITICAL: Show all pipeline steps: API → LangGraph → Gemini → BigQuery → Publishing."

    return refined


def _analyze_image_quality(extracted_text: str, stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze extracted text for quality issues.

    Checks:
    - Spelling errors
    - Duplicate text
    - Missing required numbers
    - Broken formatting
    - Readability issues

    Returns: approved (bool), issues, score, suggestions.
    """
    issues = []
    score = 100
    suggestions = []

    provider = stats.get("provider", "OpenAI")
    total = str(stats.get("total", 0))
    families = str(stats.get("family_count", 0))

    text_lower = extracted_text.lower()
    provider_lower = provider.lower()

    # Check 1: Provider name present
    if provider_lower not in text_lower:
        issues.append(f"Provider '{provider}' not found in image text")
        score -= 15
        suggestions.append(f"Ensure provider name '{provider}' is clearly visible")

    # Check 2: Key numbers present
    if total not in extracted_text:
        issues.append(f"Total model count '{total}' not found in image")
        score -= 20
        suggestions.append(f"Verify '{total} models' is displayed in metrics")
    else:
        # Check for close but wrong numbers
        wrong_totals = set()
        import re
        for match in re.finditer(r'\b(\d+)\b', extracted_text):
            num = match.group(1)
            if num != total and int(num) > 100 and int(num) < int(total) + 10:
                wrong_totals.add(num)
        if wrong_totals:
            issues.append(f"Found wrong model counts: {wrong_totals} (should be {total})")
            score -= 20

    if families not in extracted_text:
        issues.append(f"Family count '{families}' not found in image")
        score -= 15
        suggestions.append(f"Verify '{families} families' is displayed")

    # Check 3: Common misspellings
    common_misspellings = {
        "modeles": "models",
        "familise": "families",
        "recomended": "recommended",
        "compelx": "complex",
        "reasonning": "reasoning",
        "moderation": "moderation",
        "embeddings": "embeddings",
        "transcrition": "transcription",
        "geneartion": "generation",
        "vedio": "video",
        "pipleine": "pipeline",
        "discvery": "discovery",
    }

    found_misspellings = []
    for misspell, correct in common_misspellings.items():
        if misspell in text_lower:
            found_misspellings.append(f"{misspell}→{correct}")
            score -= 10

    if found_misspellings:
        issues.append(f"Spelling errors found: {', '.join(found_misspellings)}")
        suggestions.append("Regenerate image - text corruption detected")

    # Check 4: Duplicate detection
    lines = [l.strip() for l in extracted_text.split('\n') if l.strip()]
    if len(lines) != len(set(lines)):
        duplicates = [l for l in lines if lines.count(l) > 1]
        issues.append(f"Duplicate text detected: {set(duplicates)}")
        score -= 15
        suggestions.append("Regenerate - duplicate cards/labels detected")

    # Check 5: Text alignment/readability
    if len(extracted_text) < 50:
        issues.append("Very little text extracted - possible rendering issue")
        score -= 10
        suggestions.append("Check image generation - text may be too small or illegible")

    # Check 6: Category keywords
    categories = [
        "complex reasoning", "fast chat", "image generation",
        "video generation", "speech-to-text", "text-to-speech",
        "embeddings", "moderation", "realtime audio", "multimodal vision"
    ]
    found_categories = sum(1 for cat in categories if cat in text_lower)
    if found_categories < 3:
        issues.append(f"Only {found_categories} categories found (expected ≥3)")
        score -= 10

    approved = score >= 70 and len(issues) == 0
    return {
        "approved": approved,
        "issues": issues,
        "score": max(0, score),
        "suggestions": suggestions
    }
