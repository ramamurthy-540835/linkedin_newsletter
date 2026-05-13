# Multi-Agent Visual Design Pipeline Implementation

## Overview

Implemented a 4-tier multi-agent visual design system for generating premium IBM Carbon-style enterprise dashboards and architecture visuals. The pipeline transforms structured model data into production-quality Imagen prompts.

## Architecture

```
JSON Model Data
    ↓
Visual Planning Agent (gemini-2.5-pro)
    → Design Specification (layout, colors, constraints)
    ↓
UX Design Critic Agent (gemini-2.5-pro)
    → Validated & Optimized Spec
    ↓
Prompt Composer
    → Imagen-Ready Prompt
    ↓
Prompt QA Agent (gemini-2.5-flash)
    → Fact-checked, Safety-validated Prompt
    ↓
Vertex Imagen / Fallback (Matplotlib)
    ↓
(Optional) Image Quality Review Agent (stub)
    → Final Image Approval
```

## Agents Implemented

### 1. Visual Planning Agent
**Model**: `gemini-2.5-pro` (with fallback to `gemini-2.5-flash`)

Converts structured model metadata into a design specification JSON.

**Input**: 
- Provider name
- Total model count
- Family count
- Category breakdown
- High-confidence model count

**Output**: Design spec with:
- Layout structure (header, KPI metrics, category grid)
- Color palette (IBM blue #0f62fe, light backgrounds)
- Typography rules
- Visual constraints (NO dark mode, NO fake text, etc.)

**Location**: `agents/visual_design_agents.py::build_visual_design_spec()`

### 2. UX Design Critic Agent
**Model**: `gemini-2.5-pro`

Reviews design spec for compliance with IBM Carbon guidelines and identifies issues.

**Checks**:
- ✓ Light theme (no dark mode)
- ✓ Actual data (no fake/placeholder text)
- ✓ Proper spacing and hierarchy
- ✓ Feasible card layout
- ✓ Consistent alignment
- ✓ Exact metric values

**Output**: 
- `approved` (bool)
- `issues` (list)
- `suggestions` (list)
- `optimizations` (dict)
- `final_spec` (validated spec)

**Location**: `agents/visual_design_agents.py::critique_visual_spec()`

### 3. Prompt QA Agent
**Model**: `gemini-2.5-flash`

Validates Imagen prompt for factual accuracy and safety compliance.

**Fact Checks**:
- Provider mention
- Total model count exact match
- Family count exact match
- High-confidence count exact match
- Aspect ratio specification (16:9)

**Safety Checks**:
- No request for dense tables
- No request for dark theme
- No fake/placeholder text
- No cinematic hero-only visuals
- No abstract cloud art
- IBM Carbon style explicitly requested

**Output**:
- `approved` (bool)
- `fact_check_passed` (bool)
- `safety_check_passed` (bool)
- `final_prompt` (refined or original)
- `warnings`, `must_include`, `must_avoid`

**Location**: `agents/visual_design_agents.py::review_imagen_prompt_qa()`

### 4. Image Quality Review Agent (Stub)
**Model**: `gemini-2.5-flash` (multimodal, TODO)

Placeholder for post-generation image validation. Will support:
- Spell checking
- Text corruption detection
- Alignment verification
- Duplicate card detection
- Fake UI detection
- Readability assessment

**Location**: `agents/visual_design_agents.py::review_generated_image()`

## Integration Points

### Main Pipeline: `agents/publish_discovery.py`

**New function**: `generate_visual_design_pipeline()`

Orchestrates the 4-agent pipeline with graceful degradation:

```python
if enable_design_agents and _HAS_DESIGN_AGENTS:
    dashboard_prompt, mindmap_prompt, design_notes = generate_visual_design_pipeline(
        stats, visual_context, 
        style="ibm-carbon", 
        dashboard_mode="factual", 
        max_retries=3
    )
else:
    # Fallback to simple prompt generation
    dashboard_prompt, mindmap_prompt = generate_visual_prompts(visual_context)
```

**Fallback Chain**:
1. Design agents (if enabled and Gemini API available)
2. Simple prompt generation (IBM Carbon styled)
3. Matplotlib charts (built-in fallback)

### Enhanced Prompts

Updated `generate_visual_prompts()` to include explicit IBM Carbon styling:

```
Create a premium enterprise analytics dashboard visual for {provider} AI Model Registry.
Style: IBM Carbon design system - light theme, no dark mode.
Background: white / #f4f4f4 with IBM blue accents (#0f62fe).
...
Constraints: NO dark mode, NO fake text, NO tiny labels, NO dense tables, NO misspellings.
Real data only - use exact numbers: {total} models, {family_count} families.
```

## CLI Flags

### Design Agent Control
- `--enable-design-agents`: Use multi-agent pipeline (requires Gemini API)
- `--enable-image-review`: Enable image quality review (future)

### Imagen Configuration
- `--max-image-retries 3`: Max retries for image generation
- `--style ibm-carbon`: Visual style (default: ibm-carbon)
- `--dashboard-mode factual`: Dashboard mode (default: factual)

### Existing Flags (Still Supported)
- `--validate-only`: Parse and validate models only
- `--generate-image-prompts`: Generate prompts, skip Imagen/publishing
- `--use-vertex-imagen`: Call Vertex AI Imagen
- `--publish`: Post to LinkedIn and Medium

## Usage Examples

### 1. Validate Models
```bash
python agents/publish_discovery.py agents/model_discovery_candidates_openai.json --validate-only
```

Output:
- Total models: 119
- Families: 17
- High-confidence: 12
- Category breakdown

### 2. Generate IBM Carbon Prompts
```bash
python agents/publish_discovery.py agents/model_discovery_candidates_openai.json --generate-image-prompts
```

Output:
- `dashboard_raw_prompt_{ts}.txt` - IBM Carbon styled dashboard prompt
- `architecture_raw_prompt_{ts}.txt` - Architecture diagram prompt
- Matplotlib fallback charts

### 3. Use Design Agents Pipeline
```bash
python agents/publish_discovery.py agents/model_discovery_candidates_openai.json --enable-design-agents --use-vertex-imagen
```

With design agents:
- Generates design spec (Visual Planning Agent)
- Validates spec (UX Critic Agent)
- Refines prompt (Prompt QA Agent)
- Calls Vertex Imagen

### 4. Full Publishing Flow
```bash
python agents/publish_discovery.py agents/model_discovery_candidates_openai.json \
  --enable-design-agents \
  --use-vertex-imagen \
  --publish
```

## IBM Carbon Styling Details

### Colors
- **Background**: `#ffffff` (white)
- **Cards**: `#f4f4f4` (light gray)
- **Borders**: `#e0e0e0` (subtle gray)
- **Accent**: `#0f62fe` (IBM blue)
- **Text Primary**: `#161616` (dark gray)
- **Text Secondary**: `#525252` (medium gray)
- **Badges**:
  - Recommended: `#0f62fe` (IBM blue)
  - Good: `#198038` (green)
  - Niche: `#8a3ffc` (purple)
  - Deprecated: `#da1e28` (red)

### Layout
- **Aspect Ratio**: 16:9 (LinkedIn ready)
- **Header**: 12% height, blue banner with white text
- **KPI Row**: 15% height, 4 metric cards
- **Category Grid**: 73% height, 4×3 card layout
- **Typography**: Clean hierarchy, min 9pt text
- **Spacing**: Ample whitespace, soft shadows

### Constraints
- NO dark mode
- NO fake text or lorem ipsum
- NO tiny labels (< 9pt)
- NO dense tables or spreadsheets
- NO paragraphs (cards show brief text only)
- NO misspellings
- NO duplicate/overlapping cards
- NO abstract/cinematic visuals
- Real data only

## Files

### New
- `agents/visual_design_agents.py` - 4-agent system implementation

### Modified
- `agents/publish_discovery.py` - Integrated pipeline, enhanced prompts, new CLI flags

## Graceful Degradation

If Gemini API is unavailable or design agents fail:

1. **Design Agent Failure** → Falls back to simple prompt generation
2. **Imagen Unavailable** → Falls back to Matplotlib charts
3. **All Failures** → Exits gracefully with informative messages

No single point of failure breaks the entire pipeline.

## Future Enhancements

### Image Quality Review Agent
- Implement multimodal Gemini vision for post-generation validation
- Check for text spelling and corruption
- Verify layout alignment
- Detect duplicate/malformed elements
- Assess readability and contrast

### Advanced Design Agents
- Color palette optimizer (based on brand guidelines)
- Typography analyzer
- Layout validation for different card types
- Accessibility checker (contrast ratios, font sizing)

### Performance Optimization
- Batch design spec generation for multiple images
- Cache design specs for same provider
- Parallel Imagen generation with retries

## Testing

All flows tested and verified:

✅ `--validate-only` works (119 models, 17 families)
✅ Simple prompt generation with IBM Carbon styling
✅ Design agent pipeline (with graceful fallback)
✅ Matplotlib chart fallback
✅ Full publishing flow (mock)

## Notes

- Design agents use `gemini-2.5-pro` for high-quality specs, with fallback to `gemini-2.5-flash`
- Prompt QA always uses `gemini-2.5-flash` for fast validation
- All Gemini calls include detailed system prompts with IBM Carbon requirements
- Error handling ensures pipeline continues even if individual agents fail
- Generated prompts include explicit constraints to prevent hallucination
