#!/usr/bin/env python3
"""
Test: Automatic image regeneration based on quality and request matching.

Shows:
1. What was requested (in the prompt)
2. What was generated (extracted text)
3. Whether it matches the request
4. Auto-regeneration recommendations
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.visual_design_agents import (
    review_generated_image,
    validate_image_matches_request,
    _refine_prompt_from_issues
)

load_dotenv(REPO_ROOT / "backend/.env.local")
load_dotenv(REPO_ROOT / "backend/.env")

def main():
    reports_dir = REPO_ROOT / "reports"
    images = sorted(reports_dir.glob("*_vertex_*.png"), key=lambda p: os.path.getmtime(p), reverse=True)

    if not images:
        print("❌ No images found. Generate first:")
        print("   python agents/publish_discovery.py data.json --use-vertex-imagen")
        return

    test_images = images[:2]
    stats = {"provider": "OPENAI", "total": 119, "family_count": 17, "conf_buckets": {"high": list(range(12))}}

    print(f"🤖 AUTO-REGENERATION TEST")
    print(f"{'=' * 100}")
    print("\nThis simulates automatic regeneration when images don't match requests.\n")

    for img_path in test_images:
        image_type = "dashboard" if "dashboard" in img_path.name else "architecture"
        print(f"\n{'─' * 100}")
        print(f"Image: {img_path.name}")
        print(f"Type:  {image_type.upper()}")
        print(f"{'─' * 100}")

        # Get review
        review = review_generated_image(str(img_path), stats, {})

        # Show what was requested
        print(f"\n📋 WHAT WAS REQUESTED:")
        if image_type == "dashboard":
            print(f"   - Provider: OPENAI")
            print(f"   - Total Models: 119")
            print(f"   - Families: 17")
            print(f"   - High-Confidence: 12")
            print(f"   - Categories: Complex Reasoning, Image Generation, Chat, Embeddings")
            print(f"   - Style: IBM Carbon light theme")
            print(f"   - No duplicates, no spelling errors, no dark mode")
        else:
            print(f"   - Provider: OPENAI")
            print(f"   - Total Models: 119")
            print(f"   - Families: 17")
            print(f"   - Pipeline: Official API → LangGraph → Gemini → BigQuery → Publishing")
            print(f"   - Center: OPENAI Model Registry")
            print(f"   - No duplicates, no spelling errors, clean boxes and arrows")

        # Show what was generated
        print(f"\n📸 WHAT WAS GENERATED:")
        extracted = review.get("extracted_text", "")
        lines = [l.strip() for l in extracted.split('\n') if l.strip()]
        print(f"   Extracted {len(lines)} lines of text:")
        for line in lines[:10]:
            print(f"      • {line}")
        if len(lines) > 10:
            print(f"      ... ({len(lines) - 10} more)")

        # Show matching analysis
        print(f"\n✅ MATCHING ANALYSIS:")
        matches_request = review.get("matches_request")
        match_score = review.get("match_score", 0)
        print(f"   Matches Request: {matches_request}")
        print(f"   Match Score: {match_score}/100")
        print(f"   Confidence: {review.get('confidence', 'LOW')}")

        missing = review.get("missing_items", [])
        if missing:
            print(f"\n   ❌ Missing from Image:")
            for item in missing:
                print(f"      - {item}")

        # Show quality analysis
        print(f"\n📊 QUALITY ANALYSIS:")
        quality_score = review.get("quality_score", 0)
        print(f"   Quality Score: {quality_score}/100")
        quality_issues = review.get("quality_issues", [])
        if quality_issues:
            print(f"   ❌ Issues:")
            for issue in quality_issues[:5]:
                print(f"      - {issue}")
        else:
            print(f"   ✅ No quality issues")

        # Show regeneration logic
        print(f"\n🔄 AUTO-REGENERATION DECISION:")
        approved = review.get("approved")
        if approved:
            print(f"   ✅ IMAGE APPROVED - No regeneration needed")
        else:
            print(f"   ⚠️  IMAGE FAILED - Would trigger auto-regeneration")
            print(f"\n   Regeneration would:")
            print(f"      1. Detect failures (quality={quality_score}, match={match_score})")
            print(f"      2. Analyze issues: {len(missing) + len(quality_issues)} problems found")
            print(f"      3. Refine prompt with constraints:")

            # Show what prompt refinements would be
            refined = _refine_prompt_from_issues(
                "Create a premium enterprise dashboard...",
                review
            )
            if "CRITICAL:" in refined:
                additions = [line.strip() for line in refined.split("|") if "CRITICAL:" in line]
                for addition in additions:
                    print(f"         + {addition}")

            print(f"      4. Retry generation with improved prompt")
            print(f"      5. If still failing after 3 attempts: manual review required")

    print(f"\n{'=' * 100}")
    print("\n📌 To enable auto-regeneration when implemented:")
    print("   python agents/publish_discovery.py data.json \\")
    print("     --use-vertex-imagen \\")
    print("     --enable-image-review \\")
    print("     --max-image-retries 3")


if __name__ == "__main__":
    main()
