#!/usr/bin/env python3
"""
Test script: Read and analyze generated images using Gemini vision.
Checks for spelling, text corruption, alignment issues.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.visual_design_agents import review_generated_image

load_dotenv(REPO_ROOT / "backend/.env.local")
load_dotenv(REPO_ROOT / "backend/.env")

# Find the most recent images
reports_dir = REPO_ROOT / "reports"
images = list(reports_dir.glob("*_vertex_*.png"))

if not images:
    print("❌ No Vertex Imagen images found. Run with --use-vertex-imagen first:")
    print("   python agents/publish_discovery.py agents/model_discovery_candidates_openai.json \\")
    print("     --use-vertex-imagen")
    sys.exit(1)

# Get the most recent images
images.sort(key=os.path.getmtime, reverse=True)
latest_images = images[:2]  # Get the 2 most recent

print(f"📸 Analyzing {len(latest_images)} images with Gemini vision...")
print("=" * 80)

all_approved = True

for image_path in latest_images:
    print(f"\n🔍 Analyzing: {image_path.name}")
    print("-" * 80)

    # Mock stats for testing
    stats = {
        "provider": "OPENAI",
        "total": 119,
        "family_count": 17,
        "conf_buckets": {"high": list(range(12))}
    }

    result = review_generated_image(str(image_path), stats, {})

    print(f"✅ Approval: {result.get('approved', False)}")
    print(f"📊 Quality Score: {result.get('quality_score', 0)}/100")

    extracted = result.get('extracted_text', '')
    if extracted:
        print(f"\n📄 Extracted Text (first 500 chars):")
        print("-" * 80)
        print(extracted[:500])
        if len(extracted) > 500:
            print(f"... ({len(extracted) - 500} more characters)")

    issues = result.get('issues', [])
    if issues:
        print(f"\n⚠️  Issues Found ({len(issues)}):")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        all_approved = False
    else:
        print("\n✅ No issues found")

    suggestions = result.get('suggestions', [])
    if suggestions:
        print(f"\n💡 Suggestions:")
        for suggestion in suggestions:
            print(f"   - {suggestion}")

    print()

print("=" * 80)
if all_approved:
    print("✅ All images passed quality review!")
else:
    print("⚠️  Some images have quality issues. Consider regenerating.")

print("\n📌 To regenerate with corrected prompts:")
print("   python agents/publish_discovery.py agents/model_discovery_candidates_openai.json \\")
print("     --enable-design-agents --use-vertex-imagen --enable-image-review")
