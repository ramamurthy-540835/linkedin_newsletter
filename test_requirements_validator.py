#!/usr/bin/env python3
"""
Test: Requirements validator agent.
Reads requirements JSON + actual extracted text.
Reports differences without judgment.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from agents.requirements_validator import (
    load_requirements_json,
    load_actual_results,
    compare_requirements_vs_actual,
    print_comparison_report
)

load_dotenv("backend/.env.local")
load_dotenv("backend/.env")


def create_sample_requirements():
    """Create sample requirement JSON files."""

    dashboard_requirements = {
        "image_type": "dashboard",
        "provider": "OPENAI",
        "title": "OPENAI AI Model Discovery Dashboard",
        "metrics": {
            "total_models": "119",
            "model_families": "17",
            "high_confidence_models": "12"
        },
        "layout": {
            "header": "Blue banner with title",
            "kpi_section": "4 metric cards",
            "main_grid": "4x3 category cards"
        },
        "categories": [
            "Complex Reasoning",
            "Fast Chat",
            "Image Generation",
            "Video Generation",
            "Speech-to-Text",
            "Text-to-Speech",
            "Embeddings",
            "Content Moderation"
        ],
        "styling": {
            "background": "white or light gray",
            "accent_color": "IBM blue (#0f62fe)",
            "text_color": "dark gray",
            "theme": "light (no dark mode)"
        },
        "constraints": [
            "No duplicate text",
            "No spelling errors",
            "No tiny labels",
            "No fake UI elements",
            "All numbers exact"
        ]
    }

    arch_requirements = {
        "image_type": "architecture",
        "provider": "OPENAI",
        "title": "OPENAI Model Registry Architecture",
        "data": {
            "total_models": "119",
            "families": "17"
        },
        "pipeline_steps": [
            "Official API /v1/models",
            "LangGraph Discovery",
            "Gemini Enrichment",
            "BigQuery Registry",
            "Publishing Assets"
        ],
        "center_node": "OPENAI Model Registry (119 models, 17 families)",
        "visual_elements": [
            "Pipeline boxes",
            "Directional arrows",
            "Center hub"
        ],
        "constraints": [
            "No duplicate nodes",
            "No spelling errors",
            "Light background",
            "Clean arrows"
        ]
    }

    # Save requirements
    os.makedirs("test_data", exist_ok=True)

    with open("test_data/dashboard_requirements.json", "w") as f:
        json.dump(dashboard_requirements, f, indent=2)

    with open("test_data/architecture_requirements.json", "w") as f:
        json.dump(arch_requirements, f, indent=2)

    return dashboard_requirements, arch_requirements


def create_sample_actual_results():
    """Create sample actual extracted text."""

    dashboard_actual = """OPENAI AI Model Discovery Dashboard
KPI Metrics
119 Total Models
17 Families
95 High-Confidence Count
May 20, 2024
Category Name and Icon
Model Count
46 Models
Model Family
Fast Chat
Best Recommended Model
Model Framily
Model Family
Fast Chat
Best Recommended Model
46 Models
Complex Reasoning
Image Generation
Video Generation
Speech-to-Text
Embeddings
Content Moderation
No dark mode detected
Light background confirmed"""

    arch_actual = """LangGraph
Discovery
LangGraph
Discovery
Official API /v1/models
Gemini
Enrichment
OPENAI Model Registry
119 models, 17 families
BigQuory
Registory
Publishing
Assets
Clean arrows present
Light background confirmed"""

    with open("test_data/dashboard_actual.txt", "w") as f:
        f.write(dashboard_actual)

    with open("test_data/architecture_actual.txt", "w") as f:
        f.write(arch_actual)

    return dashboard_actual, arch_actual


def main():
    print("🔧 Creating sample data...")
    create_sample_requirements()
    create_sample_actual_results()
    print("   ✓ Created test_data/ with requirements and actual results\n")

    # Compare Dashboard
    print("=" * 100)
    print("TEST 1: DASHBOARD COMPARISON")
    print("=" * 100)

    print("\n📂 Loading dashboard requirements...")
    dashboard_req = load_requirements_json("test_data/dashboard_requirements.json")
    print(f"   ✓ Loaded")

    print("📂 Loading dashboard actual results...")
    dashboard_actual = load_actual_results("test_data/dashboard_actual.txt")
    print(f"   ✓ Loaded")

    print("\n🤖 Running Gemini comparison agent...")
    dashboard_comp = compare_requirements_vs_actual(dashboard_req, dashboard_actual)
    print_comparison_report(dashboard_comp)

    # Compare Architecture
    print("\n" + "=" * 100)
    print("TEST 2: ARCHITECTURE COMPARISON")
    print("=" * 100)

    print("\n📂 Loading architecture requirements...")
    arch_req = load_requirements_json("test_data/architecture_requirements.json")
    print(f"   ✓ Loaded")

    print("📂 Loading architecture actual results...")
    arch_actual = load_actual_results("test_data/architecture_actual.txt")
    print(f"   ✓ Loaded")

    print("\n🤖 Running Gemini comparison agent...")
    arch_comp = compare_requirements_vs_actual(arch_req, arch_actual)
    print_comparison_report(arch_comp)

    # Show what's possible
    print("\n" + "=" * 100)
    print("FLEXIBLE USAGE")
    print("=" * 100)
    print("""
This agent can compare ANY requirements JSON against ANY actual results.

Examples:
  1. Requirements JSON + Extracted Text
     python requirements_validator.py dashboard_req.json extracted_text.txt

  2. Requirements JSON + Extracted JSON
     python requirements_validator.py prompts_req.json actual_output.json

  3. Gemini Prompt Spec + Generated Prompt
     python requirements_validator.py prompt_spec.json generated_prompt.txt

  4. Test Case JSON + Test Results JSON
     python requirements_validator.py test_requirements.json test_results.json

The agent will ALWAYS:
  ✓ Compare fields systematically
  ✓ Report all differences
  ✓ List all matches
  ✓ Calculate coverage %
  ✓ Stay neutral (no judgment)
""")


if __name__ == "__main__":
    main()
