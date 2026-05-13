#!/usr/bin/env python3
"""
Real-world test: Compare actual prompt requirements vs actual generated image.

Takes:
  1. Prompt JSON/TXT (what we asked Imagen to generate)
  2. Generated Image (what Imagen actually created)

Reports:
  - What was requested
  - What was actually generated (extracted text)
  - Differences and coverage %
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / "backend/.env.local")
load_dotenv(REPO_ROOT / "backend/.env")

from agents.visual_design_agents import _extract_image_text
from agents.requirements_validator import (
    compare_requirements_vs_actual,
    print_comparison_report
)


def load_prompt_as_requirements(prompt_file: str) -> dict:
    """
    Load prompt text and convert to structured requirements.
    """
    with open(prompt_file) as f:
        prompt_text = f.read()

    # Parse prompt into structured requirements
    requirements = {
        "image_type": "dashboard" if "dashboard" in prompt_file.lower() else "architecture",
        "raw_prompt": prompt_text,
        "requested_elements": []
    }

    # Extract key requirements from prompt
    lines = prompt_text.split('\n')
    for line in lines:
        line = line.strip()
        if any(keyword in line.lower() for keyword in [
            'show', 'display', 'include', 'style', 'layout', 'aspect',
            'background', 'color', 'font', 'card', 'metric', 'category',
            'constraint', 'critical', 'requirement'
        ]):
            if line and len(line) > 10:
                requirements["requested_elements"].append(line)

    return requirements


def extract_and_validate(prompt_file: str, image_file: str):
    """
    Real-world validation:
    1. Load prompt requirements
    2. Extract text from generated image
    3. Compare (neutral report)
    """
    print(f"\n{'=' * 100}")
    print("REAL-WORLD IMAGE VALIDATION")
    print(f"{'=' * 100}")

    # Load prompt
    if not os.path.exists(prompt_file):
        print(f"❌ Prompt file not found: {prompt_file}")
        return

    if not os.path.exists(image_file):
        print(f"❌ Image file not found: {image_file}")
        return

    print(f"\n📄 PROMPT: {Path(prompt_file).name}")
    print(f"📸 IMAGE: {Path(image_file).name}")

    # Load requirements from prompt
    print("\n1️⃣  LOADING PROMPT REQUIREMENTS...")
    requirements = load_prompt_as_requirements(prompt_file)
    print(f"   Loaded {len(requirements['requested_elements'])} requirements")
    print(f"   Type: {requirements['image_type'].upper()}")

    # Extract text from image
    print("\n2️⃣  EXTRACTING TEXT FROM IMAGE...")
    print("   Using Gemini vision API...")
    try:
        extracted_text = _extract_image_text(image_file)
        lines = [l.strip() for l in extracted_text.split('\n') if l.strip()]
        print(f"   ✓ Extracted {len(lines)} lines of text")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # Show extracted text preview
    print("\n   📋 Extracted Text Preview:")
    for line in lines[:15]:
        print(f"      • {line}")
    if len(lines) > 15:
        print(f"      ... ({len(lines) - 15} more lines)")

    # Compare
    print("\n3️⃣  COMPARING PROMPT vs GENERATED IMAGE...")
    comparison = compare_requirements_vs_actual(requirements, extracted_text)

    # Print detailed report
    print_comparison_report(comparison)

    # Show key insights
    print(f"\n{'=' * 100}")
    print("KEY INSIGHTS")
    print(f"{'=' * 100}")

    coverage = comparison.get("coverage_percent", 0)
    matches = len(comparison.get("matches", []))
    differences = len(comparison.get("differences", []))

    print(f"\n📊 Coverage: {coverage}%")
    print(f"   {matches} requirements matched")
    print(f"   {differences} requirements not found")

    if coverage >= 90:
        print("\n✅ EXCELLENT: Image matches prompt very well")
    elif coverage >= 70:
        print("\n✅ GOOD: Image mostly matches prompt")
    elif coverage >= 50:
        print("\n⚠️  FAIR: Image partially matches prompt")
    else:
        print("\n❌ POOR: Image doesn't match prompt well")

    # Analyze what's missing
    missing = comparison.get("differences", [])
    if missing:
        print(f"\n⚠️  MISSING ({len(missing)}):")
        for diff in missing[:5]:
            req = diff.get("requirement_field", "?")
            expected = diff.get("requirement_value", "?")
            print(f"   • {req}: expected '{expected}'")
        if len(missing) > 5:
            print(f"   ... and {len(missing) - 5} more")


def find_recent_files():
    """Find most recent prompt and image files."""
    reports_dir = REPO_ROOT / "reports"

    # Find most recent dashboard files
    prompts = list(reports_dir.glob("dashboard_reviewed_prompt_*.txt"))
    images = list(reports_dir.glob("dashboard_vertex_*.png"))

    if not prompts or not images:
        return None, None

    prompts.sort(key=os.path.getmtime, reverse=True)
    images.sort(key=os.path.getmtime, reverse=True)

    return str(prompts[0]), str(images[0])


def main():
    print(f"\n🚀 REAL-WORLD IMAGE VALIDATION TEST")
    print(f"   Compares actual prompts vs actual generated images")

    if len(sys.argv) >= 3:
        # Use provided arguments
        prompt_file = sys.argv[1]
        image_file = sys.argv[2]
        print(f"\n   Using provided files:")
        print(f"     Prompt: {prompt_file}")
        print(f"     Image: {image_file}")
    else:
        # Find most recent files
        print(f"\n   Finding most recent files...")
        prompt_file, image_file = find_recent_files()

        if not prompt_file or not image_file:
            print(f"\n❌ No recent files found.")
            print(f"\n📌 Generate images first:")
            print(f"   python agents/publish_discovery.py data.json --use-vertex-imagen")
            print(f"\n📌 Or provide files manually:")
            print(f"   python test_real_image_validation.py <prompt.txt> <image.png>")
            print(f"\nExamples:")
            print(f"   python test_real_image_validation.py \\")
            print(f"     reports/dashboard_reviewed_prompt_20260513_070930.txt \\")
            print(f"     reports/dashboard_vertex_20260513_070930.png")
            return

        print(f"     Prompt: {Path(prompt_file).name}")
        print(f"     Image: {Path(image_file).name}")

    # Validate
    extract_and_validate(prompt_file, image_file)

    # Show how to use with your own files
    print(f"\n{'=' * 100}")
    print("HOW TO USE WITH YOUR OWN FILES")
    print(f"{'=' * 100}")
    print("""
Usage:
  python test_real_image_validation.py <prompt_file.txt> <image_file.png>

Examples:
  # Latest dashboard
  python test_real_image_validation.py \\
    reports/dashboard_reviewed_prompt_20260513_070930.txt \\
    reports/dashboard_vertex_20260513_070930.png

  # Latest architecture
  python test_real_image_validation.py \\
    reports/architecture_reviewed_prompt_20260513_070930.txt \\
    reports/architecture_vertex_20260513_070930.png

  # Any custom files
  python test_real_image_validation.py \\
    my_prompt.txt \\
    my_image.png

The validator will:
  1. Load prompt as requirements
  2. Extract text from image using Gemini vision
  3. Compare prompt requests vs actual image content
  4. Report coverage %, matches, and missing elements
""")


if __name__ == "__main__":
    main()
