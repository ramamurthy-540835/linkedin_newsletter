import json
from typing import Dict, Any

from visual_design_agents import (
    build_visual_design_spec,
    critique_visual_spec,
    compose_imagen_prompt_from_spec,
    review_imagen_prompt_qa,
    review_generated_image,
)


class VisualDesignOrchestrator:
    def __init__(self, design_model: str = "gemini-2.5-flash", review_model: str = "gemini-2.5-flash", theme: str = "ibm-carbon-light"):
        self.design_model = design_model
        self.review_model = review_model
        self.theme = theme

    def data_interpretation_agent(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        categories = []
        for k, models in stats.get("categorized_models", {}).items():
            best = stats.get("latest_per_usecase", {}).get(k)
            categories.append({
                "key": k,
                "count": len(models),
                "best_model": best.get("model_id") if best else None,
            })

        return {
            "total_models": stats.get("total", 0),
            "families": stats.get("family_count", 0),
            "categories": categories,
            "best_models": {k: (v.get("model_id") if v else None) for k, v in stats.get("latest_per_usecase", {}).items()},
            "high_confidence_count": len(stats.get("conf_buckets", {}).get("high", [])),
            "architecture_steps": [
                "Official API /v1/models",
                "LangGraph Discovery",
                "Gemini Enrichment",
                "BigQuery Registry",
                "Publishing Assets",
            ],
        }

    def visual_planning_agent(self, interpreted: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, Any]:
        spec_out = build_visual_design_spec(stats, style=self.theme)
        base_spec = spec_out.get("spec") or {
            "design_type": "enterprise_dashboard",
            "aspect_ratio": "16:9",
            "background": "#ffffff",
            "accent_color": "#0f62fe",
            "constraints": [],
        }
        crit = critique_visual_spec(base_spec, stats, style=self.theme)
        final_spec = crit.get("spec") or base_spec

        dashboard_plan = {
            "layout_type": "executive_dashboard",
            "theme": self.theme,
            "sections": ["kpi_header", "category_cards", "recommendations_panel"],
            "visual_constraints": [
                "white/light-gray background",
                "IBM blue accents",
                "max 6-8 category cards",
                "large KPI blocks",
                "minimal text",
                "no paragraphs",
                "no dark mode",
            ],
            "spec": final_spec,
        }
        architecture_plan = {
            "layout_type": "enterprise_architecture",
            "theme": self.theme,
            "pipeline_steps": interpreted["architecture_steps"],
            "icon_mapping": {
                "api": "cloud api",
                "langgraph": "workflow",
                "gemini": "ai spark",
                "bigquery": "database",
                "publishing": "megaphone",
            },
            "visual_constraints": [
                "icons + arrows + short labels",
                "no dense text blocks",
                "clean spacing",
                "no dark mode",
            ],
        }
        return {"dashboard": dashboard_plan, "architecture": architecture_plan}

    def prompt_composer_agent(self, plans: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, str]:
        dashboard_spec = plans["dashboard"]["spec"]
        dashboard_prompt = compose_imagen_prompt_from_spec(dashboard_spec, stats, style=self.theme)
        provider = stats.get("provider", "OPENAI")
        architecture_prompt = (
            f"Create a clean enterprise architecture infographic in IBM Carbon light style. "
            f"White/light-gray background, IBM blue accents, clear icon-based pipeline with arrows. "
            f"Show exactly these steps: {' -> '.join(plans['architecture']['pipeline_steps'])}. "
            f"Center label: {provider} Model Registry ({stats.get('total',0)} models, {stats.get('family_count',0)} families). "
            f"Use short readable labels only. No lorem ipsum. No tiny text. No dark mode. 16:9."
        )
        return {"dashboard": dashboard_prompt, "architecture": architecture_prompt}

    def prompt_qa_agent(self, prompt: str, stats: Dict[str, Any], image_type: str) -> Dict[str, Any]:
        reviewed = review_imagen_prompt_qa(prompt, stats, image_type=image_type)
        final_prompt = reviewed.get("final_prompt") or prompt
        final_prompt += (
            " | HARD CONSTRAINTS: Keep text minimal and readable; do not render fake UI widgets; "
            "no repeated labels; exact KPI values only; enterprise infographic style, not screenshot imitation."
        )
        reviewed["final_prompt"] = final_prompt
        return reviewed

    def multimodal_review_agent(self, image_path: str, stats: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        review = review_generated_image(image_path, stats, context)
        return {
            "approved": review.get("approved", False),
            "score": (0.6 * float(review.get("quality_score", 0))) + (0.4 * float(review.get("match_score", 0))),
            "issues": review.get("issues", []),
            "repair_instructions": review.get("suggestions", []),
            "raw_review": review,
        }

    def run(self, stats: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        interpreted = self.data_interpretation_agent(stats)
        plans = self.visual_planning_agent(interpreted, stats)
        prompts = self.prompt_composer_agent(plans, stats)
        dashboard_qa = self.prompt_qa_agent(prompts["dashboard"], stats, "dashboard")
        architecture_qa = self.prompt_qa_agent(prompts["architecture"], stats, "architecture")
        return {
            "interpreted": interpreted,
            "plans": plans,
            "dashboard_prompt": dashboard_qa.get("final_prompt", prompts["dashboard"]),
            "architecture_prompt": architecture_qa.get("final_prompt", prompts["architecture"]),
            "notes": {
                "design_model": self.design_model,
                "review_model": self.review_model,
                "theme": self.theme,
                "dashboard_qa": dashboard_qa,
                "architecture_qa": architecture_qa,
            },
        }
