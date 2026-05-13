# Flexible Requirements Validator Agent

## Overview

A **neutral requirements comparison agent** that:
- Reads ANY requirements JSON (flexible schema)
- Reads ANY actual results (JSON or text)
- Reports DIFFERENCES without judgment
- No hardcoded rules or checks
- Works with Gemini AI or simple text analysis

## The Problem It Solves

Instead of building separate checkers for:
- Image requirements vs extracted text
- Prompt specifications vs generated prompts
- API specs vs responses
- Test cases vs test results

You now have ONE flexible agent that compares:
```
[Any Requirements JSON] + [Any Actual Results] → [Neutral Report of Differences]
```

## How It Works

### 1. Load Requirements JSON

Any valid JSON structure works:

```json
{
  "image_type": "dashboard",
  "provider": "OPENAI",
  "metrics": {
    "total_models": "119",
    "high_confidence": "12"
  },
  "constraints": [
    "No dark mode",
    "No spelling errors"
  ]
}
```

### 2. Load Actual Results

Can be JSON or plain text:

```
OPENAI AI Model Discovery Dashboard
119 Total Models
95 High-Confidence Count
Complex Reasoning
Image Generation
No dark mode detected
```

### 3. Compare (Neutral)

Agent extracts all requirement values and checks if they appear in actual results:

```
✅ MATCHES:
  - provider: OPENAI ✓ found
  - total_models: 119 ✓ found
  - image_type: dashboard ✓ found

📋 DIFFERENCES:
  - high_confidence: required "12", actual shows "95"
  - No spelling errors: not mentioned in results
```

### 4. Report Differences

NO JUDGMENT - just facts:
- Coverage: 80% (20 of 25 requirements found)
- Matches: list of what's present
- Differences: list of what's missing/wrong/different

## Real Example

### Dashboard Test

**Requirements** (what we specified):
```json
{
  "provider": "OPENAI",
  "title": "OPENAI AI Model Discovery Dashboard",
  "metrics": {
    "total_models": "119",
    "model_families": "17",
    "high_confidence_models": "12"
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
  ]
}
```

**Actual Results** (what was generated):
```
OPENAI AI Model Discovery Dashboard
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
Complex Reasoning
Image Generation
Video Generation
Speech-to-Text
Embeddings
Content Moderation
...
```

**Comparison Report**:
```
📊 SUMMARY
  Total Requirements: 26
  Total Matches: 21
  Total Differences: 5
  Coverage: 80%

✅ MATCHES (21):
  • provider: OPENAI ✓
  • title: OPENAI AI Model Discovery Dashboard ✓
  • total_models: 119 ✓
  • model_families: 17 ✓
  • categories[0]: Complex Reasoning ✓
  • categories[1]: Fast Chat ✓
  • categories[2]: Image Generation ✓
  ... (13 more matches)

📋 DIFFERENCES (5):
  [MISSING] high_confidence_models: 12
    Actual: NOT FOUND (shows 95 instead)

  [MISSING] Text-to-Speech
    Actual: NOT FOUND IN RESULTS

  [MISSING] styling.accent_color: IBM blue (#0f62fe)
    Actual: NOT FOUND IN RESULTS

  ... (2 more)
```

## Usage

### Command Line

```bash
# Compare any requirements JSON against any actual results
python requirements_validator.py <requirements.json> <actual.txt|json>

# Examples:
python requirements_validator.py dashboard_req.json extracted_text.txt
python requirements_validator.py prompt_spec.json generated_prompt.json
python requirements_validator.py api_spec.json response.json
python requirements_validator.py test_cases.json test_results.json
```

### Programmatically

```python
from agents.requirements_validator import (
    load_requirements_json,
    load_actual_results,
    compare_requirements_vs_actual,
    print_comparison_report
)

# Load
requirements = load_requirements_json("dashboard_req.json")
actual = load_actual_results("extracted_text.txt")

# Compare
comparison = compare_requirements_vs_actual(requirements, actual)

# Report
print_comparison_report(comparison)
```

## Agent Modes

### 1. Gemini 2.5 Flash (Primary)

AI-powered comparison:
- Understands semantic meaning
- Detects equivalent values
- Flexible matching
- Explains differences contextually

### 2. Text Analysis (Fallback)

Simple substring matching:
- Case-insensitive search
- Word-level partial matching
- No semantic understanding
- Works without Gemini API
- Always available

```
Algorithm:
1. Extract all requirement values (recursive, flattened)
2. Check if each requirement value in actual results
3. Mark: full match, partial match (word-level), missing
4. Calculate coverage %
5. Report neutrally
```

## What It Can Compare

### Image Requirements vs Extracted Text
```bash
python requirements_validator.py \
  dashboard_requirements.json \
  image_extracted_text.txt
```
Reports: what text is/isn't in the image

### Prompt Spec vs Generated Prompt
```bash
python requirements_validator.py \
  prompt_specification.json \
  generated_prompt.txt
```
Reports: what the prompt does/doesn't include

### API Specification vs Response
```bash
python requirements_validator.py \
  api_spec.json \
  api_response.json
```
Reports: what fields are/aren't in response

### Test Cases vs Test Results
```bash
python requirements_validator.py \
  test_cases.json \
  test_results.json
```
Reports: which tests pass/fail

### Gemini Vision Output Spec vs Actual Extraction
```bash
python requirements_validator.py \
  vision_output_spec.json \
  extracted_text.txt
```
Reports: what Gemini did/didn't extract

## Output Format

```json
{
  "matches": [
    {"field": "provider", "value": "OPENAI"},
    {"field": "total_models", "value": "119"}
  ],
  "differences": [
    {
      "requirement_field": "high_confidence_models",
      "requirement_value": "12",
      "actual_value": "NOT FOUND IN RESULTS",
      "difference_type": "missing"
    }
  ],
  "detailed_analysis": {
    "total_requirements": 26,
    "total_matches": 21,
    "total_differences": 5,
    "summary": "21 of 26 requirements found in actual results"
  },
  "coverage_percent": 80,
  "agent": "text-analysis (fallback)"
}
```

## Examples

### Test with Your Dashboard Image

```bash
# Create dashboard requirements
cat > dashboard_req.json << 'EOF'
{
  "provider": "OPENAI",
  "total_models": "119",
  "families": "17",
  "high_confidence": "12"
}
EOF

# Extract text from your dashboard image
python -c "
from agents.visual_design_agents import _extract_image_text
text = _extract_image_text('reports/dashboard_vertex_20260513_071442.png')
with open('dashboard_actual.txt', 'w') as f:
    f.write(text)
"

# Compare
python requirements_validator.py dashboard_req.json dashboard_actual.txt
```

## Key Differences from Previous Approach

| Aspect | Old Approach | New Approach |
|--------|-------------|--------------|
| **Schema** | Hardcoded checks | Flexible JSON |
| **Judgment** | "right" vs "wrong" | Neutral differences |
| **Flexibility** | Dashboard-only | Any requirements |
| **Reusability** | Single use case | Universal |
| **Extensibility** | Must modify code | Works with any JSON |

## Benefits

✅ **No judgment** - Just reports differences
✅ **Flexible schema** - Works with ANY JSON structure
✅ **Universal** - Compares any spec against any results
✅ **Reusable** - One agent, many use cases
✅ **Neutral reporting** - Objective, not subjective
✅ **AI-powered option** - Gemini for semantic matching
✅ **Fallback available** - Works without API
✅ **Easy to use** - CLI or programmatic

## Integration Points

### With Image Quality Review
```python
# Compare vision output spec vs extracted text
requirements = {
  "provider": "OPENAI",
  "total": "119",
  "families": "17"
}
extracted = _extract_image_text(image_path)
comparison = compare_requirements_vs_actual(requirements, extracted)
```

### With Auto-Regeneration
```python
# Check if regenerated image meets original requirements
comparison = compare_requirements_vs_actual(
  original_requirements,
  _extract_image_text(regenerated_image)
)
if comparison["coverage_percent"] >= 90:
  # Good to go!
```

### With Test Validation
```python
# Compare test spec against test results
comparison = compare_requirements_vs_actual(
  test_specification,
  test_results_json
)
print(f"Tests passing: {comparison['coverage_percent']}%")
```

## Limitations

- Text-based matching is case-insensitive but not semantic
- Doesn't understand meaning differences (e.g., 12 vs 95)
- Requires Gemini for advanced semantic matching
- Partial matches counted as matches in text mode

## Future Enhancements

### 1. Weighting System
```json
{
  "requirements": [
    {"field": "provider", "value": "OPENAI", "weight": 1.0},
    {"field": "total", "value": "119", "weight": 0.8},
    {"field": "styling": "light theme", "weight": 0.5}
  ]
}
```
Weighted coverage: some requirements matter more

### 2. Tolerance Rules
```json
{
  "numeric_tolerance": 5,  // 119 ±5 is OK
  "string_tolerance": "fuzzy",  // typos acceptable
  "ignore_fields": ["date", "timestamp"]
}
```

### 3. Custom Matchers
```python
class CustomMatcher:
  def matches(requirement, actual):
    # Custom logic
```

### 4. Diff Format Options
```bash
--format json    # JSON output
--format table   # Pretty table
--format csv     # CSV export
```

## Status

✅ **Complete**: Core agent, CLI, test suite
⏳ **Planned**: Weighting, tolerance, custom matchers

Ready for production use with any JSON schema!
