# Integration Examples

## 1. CLI (Standalone)

### Basic Usage
```bash
python agents/model_discovery_langgraph_agent.py
```

### With Options
```bash
python agents/model_discovery_langgraph_agent.py --dry-run --provider openai
```

## 2. FastAPI Endpoint

Add to `backend/app/api/routes/models.py`:

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import subprocess
import json
import os
from pathlib import Path

router = APIRouter(prefix="/api/models", tags=["models"])

@router.post("/discover")
async def discover_models(
    background_tasks: BackgroundTasks,
    providers: list[str] = None,
    dry_run: bool = False
):
    """Trigger AI model discovery in background"""
    
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured")
    
    if not os.getenv("SERPAPI_KEY"):
        raise HTTPException(status_code=400, detail="SERPAPI_KEY not configured")
    
    providers = providers or ["openai", "anthropic", "google"]
    
    cmd = ["python3", "agents/model_discovery_langgraph_agent.py"]
    
    if dry_run:
        cmd.append("--dry-run")
    
    for provider in providers:
        cmd.extend(["--provider", provider])
    
    background_tasks.add_task(subprocess.run, cmd, cwd=".")
    
    return {
        "status": "discovery_started",
        "providers": providers,
        "dry_run": dry_run,
        "audit_file": "agents/model_discovery_audit.json"
    }


@router.get("/discovery/status")
async def get_discovery_status():
    """Get status of last discovery"""
    
    audit_path = Path("agents/model_discovery_audit.json")
    
    if not audit_path.exists():
        return {"status": "never_run"}
    
    with open(audit_path) as f:
        audit = json.load(f)
    
    return {
        "status": "complete",
        "started_at": audit["started_at"],
        "ended_at": audit["ended_at"],
        "discovered": audit["approved_records_count"],
        "inserts": audit["inserts_count"],
        "updates": audit["updates_count"],
        "skips": audit["skips_count"],
        "stopped": audit["stopped"],
        "stop_reason": audit.get("stop_reason", ""),
        "errors": audit.get("errors", [])
    }


@router.get("/discovery/audit")
async def get_discovery_audit():
    """Get full audit log"""
    
    audit_path = Path("agents/model_discovery_audit.json")
    
    if not audit_path.exists():
        raise HTTPException(status_code=404, detail="Audit file not found")
    
    with open(audit_path) as f:
        audit = json.load(f)
    
    return audit
```

## 3. Python Module

```python
# In your backend code
from agents.model_discovery_langgraph_agent import run_agent

# Run discovery
state = run_agent(
    provider_filter=["openai", "anthropic"],
    dry_run=False
)

print(f"Discovered: {len(state.approved_records)}")
print(f"Inserts: {len(state.inserts)}")
print(f"Updates: {len(state.updates)}")

if state.stopped:
    print(f"Failed: {state.stop_reason}")
```

## 4. Scheduled Job (Cron)

```bash
# Run discovery daily at 2 AM
0 2 * * * cd /path/to/linkedin_newsletter && \
  python3 agents/model_discovery_langgraph_agent.py \
  --provider openai --provider anthropic --provider google \
  >> /var/log/model_discovery.log 2>&1
```

## 5. Docker Container

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY agents/ ./agents/
COPY backend/app/ ./backend/app/

ENV GOOGLE_CLOUD_PROJECT=ctoteam

ENTRYPOINT ["python3", "agents/model_discovery_langgraph_agent.py"]
```

Usage:
```bash
docker build -t model-discovery .

docker run -e SERPAPI_KEY=xxx -e GEMINI_API_KEY=yyy model-discovery

# Or with options
docker run -e SERPAPI_KEY=xxx -e GEMINI_API_KEY=yyy \
  model-discovery --dry-run --provider openai
```

## 6. Cloud Function (Google Cloud)

```python
# main.py
import functions_framework
from agents.model_discovery_langgraph_agent import run_agent
import json

@functions_framework.http
def discover_models(request):
    """HTTP Cloud Function"""
    request_json = request.get_json(silent=True)
    
    providers = request_json.get("providers", ["openai", "anthropic", "google"])
    dry_run = request_json.get("dry_run", False)
    
    try:
        state = run_agent(provider_filter=providers, dry_run=dry_run)
        
        return {
            "success": True,
            "discovered": len(state.approved_records),
            "inserts": len(state.inserts),
            "updates": len(state.updates),
            "skips": len(state.skips),
            "stopped": state.stopped,
            "stop_reason": state.stop_reason
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }, 500
```

Deploy:
```bash
gcloud functions deploy discover_models \
  --runtime python311 \
  --trigger-http \
  --entry-point discover_models \
  --set-env-vars GEMINI_API_KEY=xxx,SERPAPI_KEY=xxx
```

Invoke:
```bash
curl -X POST https://region-project.cloudfunctions.net/discover_models \
  -H "Content-Type: application/json" \
  -d '{
    "providers": ["openai"],
    "dry_run": true
  }'
```

## 7. Monitoring with Audit Logs

```python
# Simple monitoring script
import json
from datetime import datetime
from pathlib import Path

audit_path = Path("agents/model_discovery_audit.json")

if audit_path.exists():
    with open(audit_path) as f:
        audit = json.load(f)
    
    elapsed = datetime.fromisoformat(audit["ended_at"]) - \
              datetime.fromisoformat(audit["started_at"])
    
    print(f"Last discovery: {audit['ended_at']}")
    print(f"Duration: {elapsed.total_seconds():.1f}s")
    print(f"Discovered: {audit['approved_records_count']}")
    print(f"Inserts: {audit['inserts_count']}")
    print(f"Updates: {audit['updates_count']}")
    print(f"Status: {'STOPPED' if audit['stopped'] else 'OK'}")
    
    if audit["errors"]:
        print(f"Errors: {audit['errors']}")
```

## 8. BigQuery Results Visualization

```sql
-- All discovered models
SELECT
  provider,
  model_id,
  display_name,
  use_case,
  speed_score,
  cost_tier,
  is_default,
  notes
FROM ctoteam.linkedin_studio.ai_models
WHERE is_active = true
ORDER BY provider, model_id;

-- Models by provider
SELECT
  provider,
  COUNT(*) as count,
  COUNTIF(is_default) as default_models,
  STRING_AGG(DISTINCT model_id, ', ') as models
FROM ctoteam.linkedin_studio.ai_models
WHERE is_active = true
GROUP BY provider
ORDER BY provider;

-- Speed vs Cost matrix
SELECT
  speed_score,
  cost_tier,
  COUNT(*) as count,
  STRING_AGG(model_id, ', ' LIMIT 5) as examples
FROM ctoteam.linkedin_studio.ai_models
WHERE is_active = true
GROUP BY speed_score, cost_tier
ORDER BY speed_score, cost_tier;
```
