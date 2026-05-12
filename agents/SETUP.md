# Quick Setup Guide

## 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## 2. Get API Keys

### SerpAPI
- Go to https://serpapi.com
- Get your API key from dashboard
- Copy to `.env` or export

### Gemini API
- Go to https://ai.google.dev
- Get your API key
- Copy to `.env` or export

### Google Cloud
```bash
# Authenticate with your Google Cloud project
gcloud auth application-default login

# Or set service account
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

## 3. Set Environment Variables

Create `.env` in project root:
```
SERPAPI_KEY=your_serpapi_key_here
GEMINI_API_KEY=your_gemini_key_here
GOOGLE_CLOUD_PROJECT=ctoteam
```

Or export in shell:
```bash
export SERPAPI_KEY="your_key"
export GEMINI_API_KEY="your_key"
export GOOGLE_CLOUD_PROJECT="ctoteam"
```

## 4. Verify Setup

```bash
# Test imports
python3 -c "
import google.generativeai as genai
import google.cloud.bigquery
import requests
print('✓ All imports OK')
"

# Test Gemini
python3 -c "
import os
import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash')
response = model.generate_content('Say hi')
print(f'✓ Gemini works: {response.text[:50]}')
"

# Test BigQuery (needs auth)
python3 -c "
from google.cloud import bigquery
client = bigquery.Client(project='ctoteam')
print('✓ BigQuery auth OK')
"
```

## 5. First Run (Dry-run)

```bash
python3 agents/model_discovery_langgraph_agent.py --dry-run
```

Expected output:
```
============================================================
MODEL DISCOVERY RESULTS
============================================================
DISCOVERED: <number>
INSERTS: <number>
UPDATES: <number>
SKIPS: <number>
STOPPED: False/True
AUDIT_FILE: agents/model_discovery_audit.json
============================================================
```

## 6. Full Run (with BigQuery writes)

```bash
python3 agents/model_discovery_langgraph_agent.py
```

## 7. Check Results

```bash
# View audit log
cat agents/model_discovery_audit.json | jq .

# Query BigQuery
bq query --use_legacy_sql=false "
SELECT provider, COUNT(*) as count
FROM ctoteam.linkedin_studio.ai_models
GROUP BY provider
ORDER BY provider
"
```

## Filtering by Provider

```bash
# OpenAI models only
python3 agents/model_discovery_langgraph_agent.py --provider openai

# Anthropic models only
python3 agents/model_discovery_langgraph_agent.py --provider anthropic

# Google models only
python3 agents/model_discovery_langgraph_agent.py --provider google

# Multiple providers
python3 agents/model_discovery_langgraph_agent.py --provider openai --provider anthropic
```

## Troubleshooting

**"SERPAPI_KEY not set"**
→ `export SERPAPI_KEY="your_key"`

**"GEMINI_API_KEY not set"**
→ `export GEMINI_API_KEY="your_key"`

**"DefaultCredentialsError"**
→ `gcloud auth application-default login`

**"Low confidence SerpAPI results"**
→ Check network, try again, or check audit log

**"No models extracted"**
→ Check SerpAPI is working, check search queries in logs

## Notes

- First run will discover models from latest API documentation
- Subsequent runs will MERGE (insert new, update changed, skip duplicates)
- Gemini 2.5 Flash is marked as default model
- BigQuery MERGE uses composite key: (provider, model_id)
- All operations are logged to `agents/model_discovery_audit.json`
