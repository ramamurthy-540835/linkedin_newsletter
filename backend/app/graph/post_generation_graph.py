from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.services.vertex_service import VertexService


class PostState(TypedDict):
    topic: str
    audience: str
    tone: str
    objective: str
    min_chars: int
    max_chars: int
    research_points: list[str]
    draft_text: str
    hashtags: list[str]
    cta: str
    compliance_notes: list[str]
    post_text: str


vertex = VertexService()


async def research_node(state: PostState) -> PostState:
    prompt = (
        "You are a LinkedIn content researcher. "
        "Given the topic and audience, return JSON with key 'research_points' as an array of 5 concise insights. "
        f"Topic: {state['topic']} Audience: {state['audience']} Objective: {state['objective']}"
    )
    data = await vertex.generate_json(prompt)
    state["research_points"] = data.get("research_points", [])[:5]
    return state


async def writer_node(state: PostState) -> PostState:
    prompt = (
        "You are a senior B2B LinkedIn ghostwriter. Return JSON with key 'draft_text'. "
        "Write a professional, specific post with short paragraphs and strong hook. "
        f"Tone: {state['tone']}. Audience: {state['audience']}. Objective: {state['objective']}. "
        f"Target chars between {state['min_chars']} and {state['max_chars']}. "
        f"Research points: {state['research_points']}"
    )
    data = await vertex.generate_json(prompt)
    state["draft_text"] = data.get("draft_text", "")
    return state


async def hashtag_optimizer_node(state: PostState) -> PostState:
    prompt = (
        "Return JSON with key 'hashtags' as 3-7 LinkedIn-ready hashtags with # prefix. "
        f"Post draft: {state['draft_text']}"
    )
    data = await vertex.generate_json(prompt)
    hashtags = data.get("hashtags", ["#Leadership", "#AI", "#Growth"])
    state["hashtags"] = [h if h.startswith("#") else f"#{h}" for h in hashtags][:7]
    return state


async def cta_optimizer_node(state: PostState) -> PostState:
    prompt = (
        "Return JSON with key 'cta'. Write one concise engagement-driving question for comments. "
        f"Draft: {state['draft_text']}"
    )
    data = await vertex.generate_json(prompt)
    state["cta"] = data.get("cta", "What is your view?")
    return state


async def compliance_node(state: PostState) -> PostState:
    text = state["draft_text"].strip()
    notes: list[str] = []
    if len(text) < state["min_chars"]:
        notes.append("below_min_chars")
        text = text + "\n\n" + " ".join(["Actionable takeaway." for _ in range(30)])
    if len(text) > state["max_chars"]:
        notes.append("above_max_chars")
        text = text[: state["max_chars"]]

    final = f"{text}\n\n{' '.join(state['hashtags'])}\n\n{state['cta']}".strip()
    if len(final) > state["max_chars"]:
        final = final[: state["max_chars"]]
        notes.append("trimmed_final")

    state["post_text"] = final
    state["compliance_notes"] = notes
    return state


def _build_graph() -> Any:
    graph = StateGraph(PostState)
    graph.add_node("research_agent", research_node)
    graph.add_node("writer_agent", writer_node)
    graph.add_node("hashtag_agent", hashtag_optimizer_node)
    graph.add_node("cta_agent", cta_optimizer_node)
    graph.add_node("compliance_agent", compliance_node)

    graph.set_entry_point("research_agent")
    graph.add_edge("research_agent", "writer_agent")
    graph.add_edge("writer_agent", "hashtag_agent")
    graph.add_edge("hashtag_agent", "cta_agent")
    graph.add_edge("cta_agent", "compliance_agent")
    graph.add_edge("compliance_agent", END)
    return graph.compile()


POST_GRAPH = _build_graph()


async def run_generation_pipeline(topic: str, audience: str, tone: str, objective: str, min_chars: int, max_chars: int) -> dict:
    init_state: PostState = {
        "topic": topic,
        "audience": audience,
        "tone": tone,
        "objective": objective,
        "min_chars": min_chars,
        "max_chars": max_chars,
        "research_points": [],
        "draft_text": "",
        "hashtags": [],
        "cta": "",
        "compliance_notes": [],
        "post_text": "",
    }
    out = await POST_GRAPH.ainvoke(init_state)
    return {
        "post_text": out["post_text"],
        "draft_text": out["draft_text"],
        "hashtags": out["hashtags"],
        "cta": out["cta"],
        "compliance_notes": out.get("compliance_notes", []),
    }
