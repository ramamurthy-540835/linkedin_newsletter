"""
requirements_validator.py

Flexible requirements validation agent.
Reads requirements JSON + actual test results.
Reports DIFFERENCES without judgment.
"""

import json
import os
import requests
from typing import Dict, Any, List

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def _call_gemini_json(prompt: str, model_name: str) -> Dict[str, Any]:
    """Call Gemini and return JSON response."""
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
        headers={"x-goog-api-key": GOOGLE_API_KEY},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
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
        raise ValueError(f"Invalid Gemini response: {data}")
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to parse Gemini response: {e}")


def load_requirements_json(file_path: str) -> Dict[str, Any]:
    """Load requirements from JSON file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Requirements file not found: {file_path}")

    with open(file_path) as f:
        return json.load(f)


def load_actual_results(file_path: str) -> Dict[str, Any] | str:
    """Load actual results (JSON or text file)."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Results file not found: {file_path}")

    with open(file_path) as f:
        content = f.read()

    # Try to parse as JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Return as plain text if not JSON
        return content


def compare_requirements_vs_actual_with_gemini(requirements: Dict[str, Any], actual: Dict[str, Any] | str) -> Dict[str, Any]:
    """
    Use Gemini agent to compare requirements vs actual results.
    """
    # Format actual as string if needed
    actual_str = actual if isinstance(actual, str) else json.dumps(actual, indent=2)

    prompt = f"""You are a neutral comparison agent. Your job is to compare requirements against actual results.

DO NOT judge which is "right" or "wrong".
DO NOT label anything as "error" or "issue".
ONLY report DIFFERENCES.

REQUIREMENTS (what was specified):
{json.dumps(requirements, indent=2)}

ACTUAL RESULTS (what was observed):
{actual_str}

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "differences": [
    {{
      "requirement_field": "field_name",
      "requirement_value": "value",
      "actual_value": "value",
      "difference_type": "missing|extra|different_value|different_format"
    }}
  ],
  "matches": [
    {{"field": "field_name", "value": "value"}}
  ],
  "detailed_analysis": {{
    "total_requirements": 0,
    "total_matches": 0,
    "total_differences": 0,
    "summary": "brief description"
  }},
  "coverage_percent": 0
}}"""

    try:
        result = _call_gemini_json(prompt, "gemini-2.5-flash")
        return result
    except Exception as e:
        return None


def compare_requirements_vs_actual(requirements: Dict[str, Any], actual: Dict[str, Any] | str) -> Dict[str, Any]:
    """
    Compare requirements vs actual results.
    Uses Gemini if available, falls back to simple text comparison.
    """
    if not GOOGLE_API_KEY:
        return {
            "error": "GOOGLE_API_KEY not set",
            "differences": [],
            "matches": [],
            "detailed_analysis": {"summary": "Gemini not configured"},
            "coverage_percent": 0,
            "agent": "fallback"
        }

    # Try Gemini
    print("   Attempting Gemini agent...", end=" ")
    result = compare_requirements_vs_actual_with_gemini(requirements, actual)

    if result:
        print("✓")
        return {
            "differences": result.get("differences", []),
            "matches": result.get("matches", []),
            "detailed_analysis": result.get("detailed_analysis", {}),
            "coverage_percent": result.get("coverage_percent", 0),
            "agent": "gemini-2.5-flash"
        }

    # Fallback: simple text-based comparison
    print("(Gemini unavailable, using text comparison)")
    return _compare_with_text_analysis(requirements, actual)


def _compare_with_text_analysis(requirements: Dict[str, Any], actual: Dict[str, Any] | str) -> Dict[str, Any]:
    """
    Simple text-based comparison as fallback.
    """
    actual_str = actual if isinstance(actual, str) else json.dumps(actual, indent=2)
    actual_lower = actual_str.lower()

    differences = []
    matches = []
    total_req = 0
    total_matches = 0

    # Extract all values from requirements
    def extract_values(obj, path=""):
        result = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                current_path = f"{path}.{k}" if path else k
                if isinstance(v, (dict, list)):
                    result.extend(extract_values(v, current_path))
                else:
                    result.append((current_path, str(v)))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                if isinstance(item, (dict, list)):
                    result.extend(extract_values(item, current_path))
                else:
                    result.append((current_path, str(item)))
        return result

    requirements_values = extract_values(requirements)

    for field, value in requirements_values:
        total_req += 1
        value_lower = str(value).lower()

        # Check if value appears in actual (case-insensitive)
        if value_lower in actual_lower or value in actual_str:
            matches.append({"field": field, "value": value})
            total_matches += 1
        else:
            # Check for partial matches
            words = value_lower.split()
            found_words = sum(1 for word in words if word in actual_lower)
            if found_words > 0:
                matches.append({"field": field, "value": f"{value} (partial match: {found_words}/{len(words)} words)"})
                total_matches += 1
            else:
                differences.append({
                    "requirement_field": field,
                    "requirement_value": value,
                    "actual_value": "NOT FOUND IN RESULTS",
                    "difference_type": "missing"
                })

    coverage = int((total_matches / total_req * 100)) if total_req > 0 else 0

    return {
        "differences": differences,
        "matches": matches,
        "detailed_analysis": {
            "total_requirements": total_req,
            "total_matches": total_matches,
            "total_differences": len(differences),
            "summary": f"{total_matches} of {total_req} requirements found in actual results"
        },
        "coverage_percent": coverage,
        "agent": "text-analysis (fallback)"
    }


def print_comparison_report(comparison: Dict[str, Any]):
    """Pretty-print comparison results."""
    print("\n" + "=" * 100)
    print("REQUIREMENTS vs ACTUAL COMPARISON REPORT")
    print("=" * 100)

    if "error" in comparison:
        print(f"\n❌ Error: {comparison['error']}")
        return

    # Summary
    analysis = comparison.get("detailed_analysis", {})
    coverage = comparison.get("coverage_percent", 0)

    print(f"\n📊 SUMMARY")
    print(f"   Total Requirements: {analysis.get('total_requirements', 0)}")
    print(f"   Total Matches: {analysis.get('total_matches', 0)}")
    print(f"   Total Differences: {analysis.get('total_differences', 0)}")
    print(f"   Coverage: {coverage}%")

    if analysis.get('summary'):
        print(f"\n   {analysis['summary']}")

    # Matches
    matches = comparison.get("matches", [])
    if matches:
        print(f"\n✅ MATCHES ({len(matches)}):")
        for match in matches[:10]:
            field = match.get("field", "?")
            value = match.get("value", "?")
            print(f"   • {field}: {value}")
        if len(matches) > 10:
            print(f"   ... and {len(matches) - 10} more")

    # Differences
    differences = comparison.get("differences", [])
    if differences:
        print(f"\n📋 DIFFERENCES ({len(differences)}):")
        for diff in differences:
            req_field = diff.get("requirement_field", "?")
            req_value = diff.get("requirement_value", "?")
            actual_value = diff.get("actual_value", "?")
            diff_type = diff.get("difference_type", "unknown")

            print(f"\n   [{diff_type.upper()}] {req_field}")
            print(f"      Required: {req_value}")
            print(f"      Actual:   {actual_value}")

    print("\n" + "=" * 100)


def main():
    """Example usage."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python requirements_validator.py <requirements.json> <actual_results.json|txt>")
        print("\nExample:")
        print("  python requirements_validator.py dashboard_requirements.json extracted_text.txt")
        return

    req_file = sys.argv[1]
    actual_file = sys.argv[2]

    print(f"📂 Loading requirements: {req_file}")
    requirements = load_requirements_json(req_file)
    print(f"   ✓ Loaded {len(requirements)} requirement items")

    print(f"📂 Loading actual results: {actual_file}")
    actual = load_actual_results(actual_file)
    print(f"   ✓ Loaded results")

    print("\n🔍 Comparing with Gemini agent...")
    comparison = compare_requirements_vs_actual(requirements, actual)

    print_comparison_report(comparison)


if __name__ == "__main__":
    main()
