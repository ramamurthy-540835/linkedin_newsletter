# Image Quality Review with Gemini Vision

## Overview

Implemented automated quality control for Vertex Imagen-generated images using Gemini's vision API. Detects spelling errors, duplicates, text corruption, and missing data in generated dashboard and architecture visuals.

## What It Does

Uses Gemini 2.5 Flash vision model to:
1. **Extract all visible text** from generated images
2. **Analyze text quality** for spelling, readability, corruption
3. **Validate data accuracy** (correct model counts, families, provider)
4. **Check for duplicates** and layout issues
5. **Generate quality score** (0-100) and recommendations

## Quality Checks

### 1. Text Extraction
- Uses Gemini vision API to read all visible text from image
- Extracts: headers, labels, numbers, badges, card titles, model names
- Returns structured text list

### 2. Spelling & Corruption Detection
Detects misspelled/corrupted text:
- `"Framily"` → should be `"Family"`
- `"Registory"` → should be `"Registry"`
- `"Premprise"` → should be `"Enterprise"`
- `"Mssštrrn"` → should be `"Dashboard"`
- Any garbled/mojibake text

### 3. Duplicate Detection
Identifies repeated text blocks:
- Duplicate card labels
- Repeated headings
- Multiple instances of same text (sign of rendering failure)

### 4. Data Validation
Ensures critical numbers appear:
- Total model count (e.g., "119 models")
- Family count (e.g., "17 families")
- Provider name (e.g., "OPENAI")
- High-confidence count

### 5. Readability Assessment
- Minimum text extraction threshold (50 characters)
- Typography visibility check
- Content density validation

### 6. Category Verification
Confirms model categories are represented:
- "Complex Reasoning", "Image Generation", "Embeddings", etc.
- Minimum 3 categories should be visible
- Warns if categories missing (layout problem)

## Quality Score Breakdown

```
100   Perfect image, no issues
85+   Excellent, minor issues only
70-84 Acceptable, some duplicates or spelling
50-69 Poor, significant issues detected
<50   Reject, needs regeneration
```

**Pass threshold**: ≥70 points

## Usage

### 1. Enable Image Review in Pipeline

```bash
python agents/publish_discovery.py data.json \
  --use-vertex-imagen \
  --enable-image-review
```

Output:
```
🔍 IMAGE QUALITY REVIEW
============================================================

⚠️  FAIL | Dashboard Image | Quality: 85/100

  📄 Extracted Text (first 300 chars):
     OPENAI AI Model Discovery Dashboard KPI Metrics 119 Total Models...

  ❌ Issues Found (1):
     - Duplicate text detected: {'Model Family', 'Model Framily', '46 Models', ...}

  💡 Suggestions:
     - Regenerate - duplicate cards/labels detected
```

### 2. Quick Test of Recent Images

```bash
python test_image_quality.py
```

Tests the 2 most recent Vertex Imagen PNGs in `reports/`.

### 3. Comprehensive Vision Extraction Demo

```bash
python test_vision_extraction.py
```

Shows full text extraction and quality analysis for all recent images.

## Real-World Examples

### Dashboard Image Issues Detected

**Image**: `dashboard_vertex_20260513_071442.png`
- **Quality Score**: 85/100
- **Issues**:
  - Duplicate: `"Model Family"` + `"Model Framily"` (spelling corruption)
  - Duplicate: `"46 Models"`, `"17"`, `"May 20, 2024"`
  - Multiple card text repeated (rendering failure)
- **Fix**: Regenerate with corrected Imagen prompt

### Architecture Image Issues Detected

**Image**: `architecture_vertex_20260513_071442.png`
- **Quality Score**: 75/100
- **Issues**:
  - Misspelled: `"BigQuory"` (should be "BigQuery")
  - Misspelled: `"Registory"` (should be "Registry")
  - Duplicate: `"LangGraph"`, `"Discovery"` (repeated in pipeline)
  - Missing: Model categories (should show ≥3)
- **Fix**: Regenerate with prompt emphasizing category visibility

## Implementation Details

### Text Extraction (`_extract_image_text`)
```python
def _extract_image_text(image_path: str) -> str:
    # Base64 encode image
    # Call Gemini vision API with prompt:
    #   "Extract ALL text visible in this image..."
    # Return extracted text list
```

### Quality Analysis (`_analyze_image_quality`)
```python
def _analyze_image_quality(extracted_text: str, stats: Dict) -> Dict:
    checks = [
        # 1. Provider presence (e.g., "OPENAI")
        # 2. Key numbers (total, families, high-confidence)
        # 3. Spelling errors (database of common mistakes)
        # 4. Duplicate text (set comparison)
        # 5. Readability (text length > 50 chars)
        # 6. Categories (≥3 should be visible)
    ]
    return {
        "approved": score >= 70,
        "issues": [list of problems],
        "score": quality_score,
        "suggestions": [regeneration tips]
    }
```

### Full Review (`review_generated_image`)
```python
def review_generated_image(image_path, stats, context) -> Dict:
    extracted = _extract_image_text(image_path)
    quality = _analyze_image_quality(extracted, stats)
    return {
        "approved": quality["approved"],
        "issues": quality["issues"],
        "extracted_text": extracted,
        "quality_score": quality["score"],
        "needs_retry": len(quality["issues"]) > 0,
        "suggestions": quality["suggestions"]
    }
```

## Integration with Pipeline

### 1. Automatic Review After Imagen
```python
if use_vertex_imagen and enable_image_review:
    dashboard_review = review_generated_image(
        dashboard_img_path, stats, context
    )
    arch_review = review_generated_image(
        mindmap_img_path, stats, context
    )
    _print_image_review(dashboard_review, "Dashboard")
    _print_image_review(arch_review, "Architecture")
```

### 2. CLI Flag
```bash
--enable-image-review    # Automatically check images after generation
```

### 3. Full Flow
```
Vertex Imagen Generation
    ↓
Image Quality Review (if --enable-image-review)
    ├─ Extract text
    ├─ Check spelling
    ├─ Check duplicates
    ├─ Check data accuracy
    └─ Score 0-100
    ↓
Report Issues & Suggestions
    ├─ ✅ Pass (≥70) → Continue
    └─ ⚠️  Fail (<70) → Suggest regeneration
```

## Future Enhancements

### 1. Auto-Regeneration Loop
```python
for attempt in range(max_retries):
    image = call_vertex_imagen(prompt)
    review = review_generated_image(image)
    if review["approved"]:
        break
    # Refine prompt based on issues
    # Retry with improved prompt
```

### 2. Prompt Refinement
Use review feedback to auto-improve prompts:
- `"Ensure NO duplicate text"`
- `"Make categories clearly visible"`
- `"Spell all words correctly"`

### 3. Layout Validation
- Bounding box detection for card alignment
- Text overlap detection
- Spacing validation

### 4. Brand Compliance
- Color accuracy checking
- IBM Carbon style verification
- Font consistency validation

### 5. A/B Testing
- Compare multiple generations
- Select highest-quality version
- Track improvement over time

## Files

### New
- `agents/visual_design_agents.py::_extract_image_text()` - Gemini vision text extraction
- `agents/visual_design_agents.py::_analyze_image_quality()` - Quality analysis
- `agents/visual_design_agents.py::review_generated_image()` - Full review
- `test_image_quality.py` - Quick test of 2 recent images
- `test_vision_extraction.py` - Comprehensive demo

### Modified
- `agents/publish_discovery.py` - Integrated image review with CLI flag
- `agents/publish_discovery.py::_print_image_review()` - Pretty print results

## Troubleshooting

### "GEMINI_API_KEY not set"
```bash
# Ensure env var is set
export GEMINI_API_KEY="your-key-here"
# Or add to backend/.env
```

### "Image not found"
Generate images first:
```bash
python agents/publish_discovery.py data.json --use-vertex-imagen
```

### Vision extraction returns empty
- Check image is valid PNG
- Verify image has visible text
- Try with recent image (test with --latest)

## Example Output

```
🔬 GEMINI VISION TEXT EXTRACTION TEST
================================================================================

[1] dashboard_vertex_20260513_071442.png
   Extracting text...
   ✅ Extracted 47 lines of text:
      1. OPENAI AI Model Discovery Dashboard
      2. KPI Metrics
      3. 119
      4. Total Models
      ...
   
   Running quality checks...
   Score: 85/100
   Status: ⚠️  NEEDS REGEN
   
   Issues:
      ❌ Duplicate text: 'Model Family', 'Model Framily'
      ❌ Duplicate text: '46 Models', '17'
   
   Fix:
      💡 Regenerate - duplicate cards/labels detected
```

## Notes

- Vision API calls use Gemini 2.5 Flash for speed & cost
- Misspelling detection uses curated database of common Imagen errors
- Score ≥70 considered acceptable (minor issues OK for publishing)
- Text extraction typically 50-100 lines per image
- First image analysis takes ~5-10 seconds (Gemini vision latency)
