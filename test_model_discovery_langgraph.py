import os
import json
import requests
from typing import TypedDict, List
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv(".env.local")
load_dotenv(".env.local", override=True)

if os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

if os.getenv("SERAPI_KEY"):
    os.environ["SERPAPI_KEY"] = os.getenv("SERAPI_KEY")

os.environ.pop("GOOGLE_GENAI_API_KEY", None)

if not os.getenv("SERPAPI_KEY") and os.getenv("SERAPI_KEY"):
    os.environ["SERPAPI_KEY"] = os.getenv("SERAPI_KEY")

if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

print("Using Gemini key:", "YES" if os.getenv("GOOGLE_API_KEY") else "NO")
print("Using SerpAPI key:", "YES" if os.getenv("SERPAPI_KEY") else "NO")

if not os.getenv("GOOGLE_API_KEY"):
    raise RuntimeError("Missing GOOGLE_API_KEY (mapped from GEMINI_API_KEY)")
if not os.getenv("SERPAPI_KEY"):
    raise RuntimeError("Missing SERPAPI_KEY (mapped from SERAPI_KEY)")

def parse_json(text):
    clean = text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.environ["GOOGLE_API_KEY"],
    temperature=0
)

try:
    test = llm.invoke("Say hello")
    print(test.content)
except Exception as e:
    raise RuntimeError(f"Gemini preflight failed: {e}")

class DiscoveryState(TypedDict):
    provider: str
    search_queries: List[str]
    serp_results: List[dict]
    extracted_models: List[dict]

def generate_queries(state):
    print("\n=== GEMINI SEARCH STRATEGY ===")

    prompt = f"""
You are an AI model discovery planner.

Goal:
Find official model IDs for provider: {state["provider"]}

Generate 3 high-precision Google search queries.

Rules:
- Prefer official vendor docs.
- For OpenAI, prefer developers.openai.com and openai.com/api/pricing.
- Avoid blogs/community sites.
- Return JSON only.

Format:
[
  "query 1",
  "query 2",
  "query 3"
]
"""

    resp = llm.invoke([HumanMessage(content=prompt)])
    print(resp.content)

    return {"search_queries": parse_json(resp.content)}

def serp_search(state):
    print("\n=== SERP SEARCH ===")

    all_results = []

    for q in state["search_queries"]:
        print(f"\nSearching: {q}")

        params = {
            "engine": "google",
            "q": q,
            "api_key": os.environ["SERPAPI_KEY"],
            "num": 5
        }

        r = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
        data = r.json()

        if "error" in data:
            print("SERPAPI ERROR:", data["error"])
            continue

        organic = data.get("organic_results", [])
        all_results.extend(organic)

        print(f"Found {len(organic)}")
        for i, item in enumerate(organic[:3], 1):
            print(f"{i}. {item.get('title')}")
            print(f"   {item.get('link')}")

    return {"serp_results": all_results}

def extract_models(state):
    print("\n=== GEMINI EXTRACTION ===")

    text = ""

    for item in state["serp_results"]:
        text += f"""
Title: {item.get("title")}
URL: {item.get("link")}
Snippet: {item.get("snippet")}
"""

        for s in item.get("sitelinks", {}).get("expanded", []):
            text += f"""
Sitelink: {s.get("title")}
Link: {s.get("link")}
Snippet: {s.get("snippet")}
"""

    prompt = f"""
Extract official model IDs for provider {state["provider"]}.

Return JSON only. No markdown.

Format:
[
  {{
    "model_id": "gpt-5.5",
    "provider": "openai",
    "display_name": "GPT-5.5"
  }}
]

Use only models clearly visible in titles, URLs, snippets, or sitelinks.

Search data:
{text}
"""

    resp = llm.invoke([HumanMessage(content=prompt)])
    print(resp.content)

    try:
        parsed = parse_json(resp.content)
    except Exception as e:
        print("JSON parse failed:", e)
        parsed = []

    return {"extracted_models": parsed}

graph = StateGraph(DiscoveryState)
graph.add_node("plan", generate_queries)
graph.add_node("search", serp_search)
graph.add_node("extract", extract_models)

graph.set_entry_point("plan")
graph.add_edge("plan", "search")
graph.add_edge("search", "extract")
graph.add_edge("extract", END)

app = graph.compile()

result = app.invoke({"provider": "openai"})

print("\n=== FINAL ===")
print(json.dumps(result, indent=2))
