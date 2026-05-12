# AI Model Discovery Agent

Advanced AI model discovery using **LangGraph** + **Gemini 2.5 Flash** + **SerpAPI** + **BigQuery**.

## Setup

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export SERPAPI_KEY="your_serpapi_key"
   export GEMINI_API_KEY="your_gemini_api_key"
   export GOOGLE_CLOUD_PROJECT="ctoteam"
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"  # Optional
   ```

   Or add to `.env`:
   ```
   SERPAPI_KEY=your_key
   GEMINI_API_KEY=your_key
   GOOGLE_CLOUD_PROJECT=ctoteam
   ```

## Usage

### Basic Run (All Providers)
```bash
python agents/model_discovery_langgraph_agent.py
```

### Dry Run (Preview without BigQuery write)
```bash
python agents/model_discovery_langgraph_agent.py --dry-run
```

### Filter by Provider
```bash
# OpenAI only
python agents/model_discovery_langgraph_agent.py --provider openai

# Anthropic only
python agents/model_discovery_langgraph_agent.py --provider anthropic

# Google only
python agents/model_discovery_langgraph_agent.py --provider google

# Multiple providers
python agents/model_discovery_langgraph_agent.py --provider openai --provider anthropic
```

### Dry Run with Provider Filter
```bash
python agents/model_discovery_langgraph_agent.py --dry-run --provider openai
```

## Workflow

The agent executes a 12-node LangGraph pipeline:

1. **build_search_queries** — Create provider-specific searches
2. **validate_queries_with_gemini** — Validate queries for safety/clarity
3. **serpapi_search** — Execute web searches
4. **validate_serp_results_with_gemini** — Validate search results (official sources, relevance, confidence ≥ 70%)
5. **extract_models** — Extract model IDs using regex patterns
6. **normalize_and_classify** — Classify by speed_score, cost_tier, use_case
7. **validate_final_records_with_gemini** — Validate normalized records
8. **fetch_existing_bigquery_models** — Query existing models
9. **diff_records** — Diff approved vs. existing (inserts, updates, skips)
10. **merge_to_bigquery** — MERGE/upsert to BigQuery
11. **write_audit** — Write JSON audit log
12. **end** — Done

## Output

### Console Output
```
============================================================
MODEL DISCOVERY RESULTS
============================================================
DISCOVERED: 42
INSERTS: 15
UPDATES: 3
SKIPS: 24
STOPPED: False
AUDIT_FILE: agents/model_discovery_audit.json
============================================================
```

### Audit Log
File: `agents/model_discovery_audit.json`

```json
{
  "started_at": "2025-05-12T10:30:45.123456Z",
  "ended_at": "2025-05-12T10:33:22.654321Z",
  "queries_count": 8,
  "serp_results_count": 47,
  "approved_records_count": 42,
  "inserts_count": 15,
  "updates_count": 3,
  "skips_count": 24,
  "stopped": false,
  "stop_reason": "",
  "errors": [],
  "dry_run": false
}
```

## Safety Features

### Gemini Validation at Every Step
- ✅ Search queries validated for safety/clarity
- ✅ SerpAPI results validated for official sources + confidence ≥ 70%
- ✅ Final records validated for garbage/duplicates/invalid providers

### Graceful Failure
- ❌ If any validation fails → STOP (don't write bad data)
- ❌ If SerpAPI returns irrelevant results → STOP
- ❌ If extracted records are empty → STOP
- ❌ If Gemini confidence < 70% → STOP

### BigQuery Safety
- ✅ Never deletes existing rows
- ✅ Uses MERGE to prevent duplicates (key: provider + model_id)
- ✅ Only inserts/updates, never overwrites schema
- ✅ Dry-run mode for preview without writes

### Model Defaults
- Gemini 2.5 Flash is marked `is_default = true`
- All others default to `is_default = false`

## Classification

Models are automatically classified:

| Type | Speed Score | Cost Tier |
|------|-------------|-----------|
| Flash, Mini, Nano, Lite, Haiku | 3 (Fast) | 1 (Cheap) |
| Sonnet, GPT-4o, Gemini Pro | 2 (Balanced) | 2 (Balanced) |
| Opus, Pro, O3, O4, Deep-Research | 1 (Slow) | 3 (Expensive) |

Use cases auto-detected from model_id:
- `embedding` → embedding, semantic_search, rag
- `imagen` → image_generation, creative
- `veo` → video_generation, creative
- `gemma` → chat, cost, automation
- Default → chat, general, automation

## BigQuery Schema

```sql
CREATE TABLE `ctoteam.linkedin_studio.ai_models` (
  model_id STRING,          -- e.g., "gpt-4o", "claude-3-opus", "models/gemini-2.5-flash"
  provider STRING,          -- "openai", "anthropic", "google"
  display_name STRING,      -- e.g., "GPT 4o"
  use_case STRING,          -- comma-separated: "chat,coding,reasoning"
  speed_score INT64,        -- 1-3 (lower = faster)
  cost_tier INT64,          -- 1-3 (higher = more expensive)
  is_default BOOL,          -- true for Gemini 2.5 Flash
  is_active BOOL,           -- true for discovered models
  notes STRING              -- source link, discovery timestamp
);
```

## Troubleshooting

### Missing SERPAPI_KEY
```
ERROR: SERPAPI_KEY not set
Install with: pip install requests
```
→ Set `export SERPAPI_KEY="your_key"`

### Missing GEMINI_API_KEY
```
ERROR: GEMINI_API_KEY not set
```
→ Set `export GEMINI_API_KEY="your_key"`

### BigQuery Authentication Error
```
google.auth.exceptions.DefaultCredentialsError
```
→ Run `gcloud auth application-default login` or set `GOOGLE_APPLICATION_CREDENTIALS`

### Low Gemini Confidence
```
STOPPED: Low confidence SerpAPI results
```
→ Check SerpAPI results manually or try again later

### No Models Extracted
```
STOPPED: No models extracted from search results
```
→ Check search queries in audit log, may need manual intervention

## Advanced

### Check Audit Details
```bash
cat agents/model_discovery_audit.json | jq .
```

### Query Discovered Models
```bash
bq query --use_legacy_sql=false "
SELECT provider, model_id, display_name, use_case, speed_score, cost_tier, is_default
FROM ctoteam.linkedin_studio.ai_models
WHERE is_active = true
ORDER BY provider, model_id
"
```

### Verify MERGE Updated Correctly
```bash
bq query --use_legacy_sql=false "
SELECT COUNT(*) as total_models, COUNT(DISTINCT model_id) as unique_models
FROM ctoteam.linkedin_studio.ai_models
"
```
