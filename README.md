# LinkedIn Post Creation Agent

AI-powered LinkedIn post generator inspired by the Medium Agent architecture.

## Stack
- Backend: FastAPI + LangGraph + Vertex AI Gemini 2.5 Flash
- Frontend: Next.js 14 + React
- Data: Firestore
- Scheduling: Cloud Tasks
- Deployment: Cloud Run
- Realtime: SSE

## Local setup
### Backend
- `cd backend`
- `python3 -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`
- `cp .env.example .env`
- `uvicorn app.main:app --reload --port 8000`

### Frontend
- `cd frontend`
- `npm install`
- `cp .env.local.example .env.local`
- `npm run dev`
