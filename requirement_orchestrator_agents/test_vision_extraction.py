#!/usr/bin/env python3
"""
Test: Extract text from Vertex Imagen generated images using Gemini vision.
Demonstrates spell-checking and quality control for generated images.

Usage:
  python test_vision_extraction.py [--latest]

Examples:
  python test_vision_extraction.py
    → Analyzes the 2 most recent Vertex Imagen PNG files

  python test_vision_extraction.py --latest
    → Same as default
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.visual_design_agents import review_generated_image, _extract_image_text

load_dotenv(REPO_ROOT / "backend/.env.local")
load_dotenv(REPO_ROOT / "backend/.env")

def main():
    # Find the most recent images
    reports_dir = REPO_ROOT / "reports"
    images = sorted(reports_dir.glob("*_vertex_*.png"), key=lambda p: os.path.getmtime(p), reverse=True)

    if not images:
        print("❌ No Vertex Imagen images found in reports/")
        print("\n📌 Generate images first:")
        print("   python agents/publish_discovery.py data.json --use-vertex-imagen")
        return

    test_images = images[:2]  # Test 2 most recent

    print(f"🔬 GEMINI VISION TEXT EXTRACTION TEST")
    print(f"{'=' * 80}")
    print(f"Testing {len(test_images)} images\n")

    for i, img_path in enumerate(test_images, 1):
        print(f"[{i}] {img_path.name}")
        print(f"{'-' * 80}")

        try:
            # Extract text
            print("   Extracting text with Gemini vision...")
            extracted = _extract_image_text(str(img_path))

            # Show extraction
            lines = extracted.split('\n')
            print(f"   ✅ Extracted {len(lines)} lines of text:\n")

            for j, line in enumerate(lines[:20], 1):  # Show first 20 lines
                if line.strip():
                    print(f"      {j:2d}. {line}")

            if len(lines) > 20:
                print(f"      ... ({len(lines) - 20} more lines)")

            # Analyze quality
            print(f"\n   Running quality checks...")
            stats = {"provider": "OPENAI", "total": 119, "family_count": 17, "conf_buckets": {"high": list(range(12))}}
            result = review_generated_image(str(img_path), stats, {})

            print(f"   Score: {result.get('quality_score', 0)}/100")
            approved = result.get('approved', False)
            print(f"   Status: {'✅ PASS' if approved else '⚠️  NEEDS REGEN'}")

            issues = result.get('issues', [])
            if issues:
                print(f"\n   Issues:")
                for issue in issues:
                    print(f"      ❌ {issue}")

            suggestions = result.get('suggestions', [])
            if suggestions:
                print(f"\n   Fix:")
                for sug in suggestions:
                    print(f"      💡 {sug}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

    print(f"{'=' * 80}")
    print("\n📌 Usage Examples:\n")
    print("1. Generate images with quality review:")
    print("   python agents/publish_discovery.py data.json \\")
    print("     --use-vertex-imagen --enable-image-review\n")

    print("2. Re-run generation (will fix quality issues):")
    print("   python agents/publish_discovery.py data.json \\")
    print("     --enable-design-agents --use-vertex-imagen --enable-image-review\n")

    print("3. Extract and analyze existing images:")
    print("   python test_vision_extraction.py\n")


if __name__ == "__main__":
    main()
