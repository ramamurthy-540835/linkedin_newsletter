# LinkedIn Newsletter Agent

AI-powered LinkedIn post creation and publishing agent inspired by a Medium-agent pattern.

## What We Built

### Backend (FastAPI)
- FastAPI service with modular routes:
  - `GET /health`
  - `POST /api/generate`
  - `POST /api/generate/stream` (SSE progress)
  - `GET /api/auth/linkedin/url`
  - `GET /api/auth/linkedin/callback`
  - `POST /api/drafts`
  - `POST /api/publish`
  - `POST /api/schedule`
  - `GET /api/analytics/summary`
- CORS enabled for local frontend integration.

### AI Generation (LangGraph + Vertex AI Gemini)
- Multi-agent graph pipeline for post generation:
  - `research_agent`
  - `writer_agent`
  - `hashtag_agent`
  - `cta_agent`
  - `compliance_agent`
- Model: `gemini-2.5-flash` via Vertex AI.
- Output includes:
  - LinkedIn post text
  - optimized hashtags
  - CTA
  - character-bound enforcement (500–2000 configurable)

### LinkedIn OAuth2 + Real Publishing
- OAuth URL generation and code-to-token exchange implemented.
- Real publishing implemented with LinkedIn UGC API (`/v2/ugcPosts`).
- Uses:
  - `LINKEDIN_ACCESS_TOKEN`
  - `LINKEDIN_AUTHOR_URN`

### Draft/Publish Storage
- Initial Firestore integration failed on Datastore-mode GCP project.
- Switched to local JSON storage for immediate usability:
  - `backend/data/drafts.json`
  - `backend/data/posts.json`
- Endpoints remain unchanged, so frontend integration is stable.

## Project Structure

- `backend/` FastAPI + LangGraph + LinkedIn integration
- `frontend/` Next.js 14 starter UI
- `infra/` deployment placeholders
- `scripts/` utility placeholders

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Required Backend Env

Set these in `backend/.env`:

```env
APP_NAME=LinkedIn Post Agent
ENV=dev
HOST=0.0.0.0
PORT=8000

GCP_PROJECT_ID=ctoteam
GCP_REGION=us-central1
VERTEX_MODEL=gemini-2.5-flash

LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_REDIRECT_URI=http://10.100.15.44:8000/api/auth/linkedin/callback
LINKEDIN_AUTHOR_URN=urn:li:person:...
LINKEDIN_ACCESS_TOKEN=...

CLOUD_TASKS_QUEUE=linkedin-post-schedule
CLOUD_TASKS_LOCATION=us-central1
CLOUD_RUN_BASE_URL=http://10.100.15.44:8000
```

## Run Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## OAuth + URN Setup

1. LinkedIn App redirect URL must exactly match:
   - `http://10.100.15.44:8000/api/auth/linkedin/callback`
2. Get auth URL:

```bash
curl -s "http://10.100.15.44:8000/api/auth/linkedin/url?state=test123"
```

3. Open returned URL, approve. Callback returns token JSON.
4. Save `token.access_token` to `LINKEDIN_ACCESS_TOKEN`.
5. Fetch profile:

```bash
curl -s -H "Authorization: Bearer <ACCESS_TOKEN>" "https://api.linkedin.com/v2/userinfo"
```

6. Set URN using `sub`:
   - `LINKEDIN_AUTHOR_URN=urn:li:person:<sub>`

## API Test Flow (Real)

### 1) Generate post
```bash
curl -s -X POST "http://10.100.15.44:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"topic":"How I built an AI agent for LinkedIn newsletters","audience":"founders and product leaders","tone":"professional","objective":"engagement","min_chars":700,"max_chars":1500}'
```

### 2) Create draft
```bash
curl -s -X POST "http://10.100.15.44:8000/api/drafts" \
  -H "Content-Type: application/json" \
  -d '{"title":"Built AI Agent for LinkedIn Newsletter","content":"<PASTE_POST_TEXT>","hashtags":["#AI","#LinkedIn"],"cta":"What would you automate first?"}'
```

### 3) Publish to LinkedIn
```bash
curl -s -X POST "http://10.100.15.44:8000/api/publish" \
  -H "Content-Type: application/json" \
  -d '{"draft_id":"<PASTE_DRAFT_ID>"}'
```

On success, returns `linkedin_post_id` like:
- `urn:li:share:...`
- URL format: `https://www.linkedin.com/feed/update/<URN>/`

## Frontend Starter

### Run frontend
```bash
cd frontend
npm install
npm run dev -- -H 0.0.0.0 -p 3000
```

Open:
- `http://10.100.15.44:3000/`
- `http://10.100.15.44:3000/draft`

## Frontend Build Prompt (for your local implementation)

Use this prompt to continue frontend work:

"Build a production-grade Next.js 14 frontend for this backend API. Add end-to-end Draft -> Generate -> Save -> Publish workflow. Requirements:
1. Draft page with fields: topic, audience, tone, objective, min_chars, max_chars.
2. Call `POST /api/generate` and show generated text, hashtags, CTA in editable form.
3. Save draft via `POST /api/drafts` and persist returned `draft_id`.
4. Publish button calls `POST /api/publish` with `draft_id`.
5. Show publish success including `linkedin_post_id` and clickable LinkedIn URL.
6. Add SSE mode using `POST /api/generate/stream` with stage-wise progress bar.
7. Add pages for Drafts history and Publish history from local JSON-backed endpoints (or add new list endpoints).
8. Use clean responsive UI, loading/error states, and toasts.
9. Keep API base URL configurable via `NEXT_PUBLIC_API_BASE_URL`.
10. Add basic auth/session placeholder boundary for multi-user future support."

## Known Notes

- Current draft/post storage is local JSON for quick reliability.
- Firestore Native mode is required if you re-enable Firestore client usage.
- Rotate all secrets/tokens that were ever exposed in terminal/chat logs.

## Next Recommended Improvements

1. Add token refresh handling using LinkedIn refresh token.
2. Add `GET /api/drafts` and `GET /api/posts` endpoints for UI lists.
3. Add BigQuery persistence mode for production analytics/audit.
4. Add scheduled publishing worker path with Cloud Tasks and signed service auth.
5. Add tests for routes and publish failure paths.


## 📊 Latest Model Discovery Run

| Field | Value |
|-------|-------|
| Provider | OPENAI |
| Run Date | 20260512T1 |
| Total Models | 119 |
| Families | 13 |
| High Confidence | N/A |
| Needs Review | N/A |
| LinkedIn Post | N/A |
| Medium Article | N/A |
| Dashboard Visual | N/A |
| Mindmap Visual | N/A |

