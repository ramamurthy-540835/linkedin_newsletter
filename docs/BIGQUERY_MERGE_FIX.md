# BigQuery MERGE Duplication Bug Fix

## Problem
OpenAI table had 242 rows but only 119 unique model_ids, indicating duplicate rows were being created by the MERGE operation.

## Root Cause
The original `insert_rows_json()` approach was inserting all rows without checking for or handling duplicates. This caused:
- Multiple rows per model_id (242 rows for 119 unique models)
- No proper MERGE logic to match existing records
- No deduplication of source data

## Solution

### 1. Preflight Duplicate Detection
Before upserting, the system now checks for existing duplicates:
```sql
SELECT provider, model_id, COUNT(*)
FROM table
GROUP BY provider, model_id
HAVING COUNT(*) > 1
```

If duplicates are found, the process stops with a clear error message.

### 2. Duplicate Repair (Optional)
Use `--repair-duplicates` flag to safely remove duplicate rows:
```bash
python agents/model_discovery_langgraph_agent.py --target-provider openai --repair-duplicates
```

Repair logic:
- Keeps only the row with latest `last_verified_at` per provider/model_id
- Removes all other duplicates
- Uses SQL DELETE with MAX(last_verified_at) subquery

### 3. Source Row Deduplication
Before inserting, source rows are deduplicated by provider/model_id:
- If multiple rows have same provider + model_id
- Keep the one with latest `last_verified_at` timestamp
- Prevents duplicate inserts from source data

### 4. Match Key Definition
MERGE/UPDATE matches ONLY on:
- T.provider = S.provider
- T.model_id = S.model_id

Does NOT include:
- Timestamps (discovered_at, last_verified_at, first_seen_at)
- version_history
- family
- version
- release_stage
- status

## Usage

### Run Discovery
```bash
# Normal run (will stop if duplicates exist)
python agents/model_discovery_langgraph_agent.py --target-provider openai

# If duplicates exist, fix them:
python agents/model_discovery_langgraph_agent.py --target-provider openai --repair-duplicates
```

### Verify Results
After successful run, check BigQuery:
```sql
-- Check for duplicates
SELECT provider, model_id, COUNT(*) as cnt
FROM `project.linkedin_studio.ai_models`
GROUP BY provider, model_id
HAVING COUNT(*) > 1;

-- Should return: 0 rows (no duplicates)

-- Check totals
SELECT 
  COUNT(*) as total_rows,
  COUNT(DISTINCT CONCAT(provider, ':', model_id)) as unique_models
FROM `project.linkedin_studio.ai_models`
WHERE provider = 'openai';

-- Should return: total_rows = unique_models = 119
```

## Output Format
Discovery now shows BigQuery verification after upsert:
```
Upserted 119 models to BigQuery
  Inserts: 115
  Updates: 4
  BigQuery after upsert: 119 total rows, 119 unique models
```

The verification query confirms:
- total_rows = 119 (all models stored)
- unique_models = 119 (no duplicates)

## Technical Details

### Deduplication Logic
```python
dedup_map = {}
for row in rows_to_insert:
    key = (row.get("provider"), row.get("model_id"))
    if key not in dedup_map:
        dedup_map[key] = row
    else:
        existing = dedup_map[key]
        current_time = row.get("last_verified_at", "")
        existing_time = existing.get("last_verified_at", "")
        if current_time > existing_time:
            dedup_map[key] = row
```

### Repair SQL
```sql
DELETE FROM `{table_id}`
WHERE CONCAT(provider, ':', model_id, ':', CAST(last_verified_at AS STRING)) NOT IN (
    SELECT CONCAT(provider, ':', model_id, ':', CAST(MAX(last_verified_at) AS STRING))
    FROM `{table_id}`
    GROUP BY provider, model_id
)
```

## Commits
- `c4d232a` - Add BigQuery duplicate detection and repair system
- `012942c` - Improve source deduplication to keep latest timestamp

## Future Improvements
1. Implement true MERGE statement (if BigQuery supports it for this use case)
2. Add transaction safety (all-or-nothing upsert)
3. Monitor duplicate creation patterns to prevent future occurrences
4. Add logging to track which models are being inserted vs updated
