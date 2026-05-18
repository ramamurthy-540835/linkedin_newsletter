#!/usr/bin/env python3
"""
Test available models in ctoteam from linkedin_studio.project_available_models.

Usage:
  python scripts/test_available_models.py                          # Test active models (API calls)
  python scripts/test_available_models.py --query                  # Show active models only (no API)
  python scripts/test_available_models.py --all                    # Show ALL models (active + unreachable + denied)
  python scripts/test_available_models.py --prompt "What is AI?"   # Custom prompt
  python scripts/test_available_models.py --publisher google       # Filter by publisher
  python scripts/test_available_models.py --type reasoning         # Filter by type
  python scripts/test_available_models.py --update-status          # Test + update BQ status
"""

import argparse
import json
import os
from datetime import datetime, timezone

import google.auth
import google.auth.transport.requests
import requests as http_requests
from google.cloud import bigquery


PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "ctoteam")
DATASET = os.getenv("BQ_DATASET", "linkedin_studio")
TABLE = f"{PROJECT}.{DATASET}.project_available_models"

REGION_MAP = {
    "anthropic": ["us-east5", "europe-west1", "us-central1"],
    "xai": ["us-central1", "us-east5"],
    "meta": ["us-central1", "us-east5"],
    "google": ["us-central1"],
}


def query_available_models(publisher=None, model_type=None, show_all=False):
    client = bigquery.Client(project=PROJECT)
    where = [] if show_all else ["is_available = TRUE"]
    if publisher:
        where.append(f"publisher = '{publisher}'")
    if model_type:
        where.append(f"model_type = '{model_type}'")
    where_clause = "WHERE " + " AND ".join(where) if where else ""

    rows = list(client.query(f"""
        SELECT publisher, model_id, display_name, family, model_type,
               vertex_model_path, vertex_region, endpoint_method,
               supported_actions, status, is_available
        FROM `{TABLE}`
        {where_clause}
        ORDER BY is_available DESC, publisher, model_type, model_id
    """).result())

    if show_all:
        print(f"\n{'Status':<14} {'Publisher':<12} {'Model ID':<42} {'Type':<15} {'Region':<14} {'Display Name'}")
        print("-" * 115)
        for r in rows:
            region = getattr(r, 'vertex_region', '') or '-'
            print(f"{r.status:<14} {r.publisher:<12} {r.model_id:<42} {r.model_type:<15} {region:<14} {r.display_name}")
        active = sum(1 for r in rows if r.is_available)
        print(f"\nTotal: {len(rows)} | Active: {active} | Unreachable: {sum(1 for r in rows if r.status=='unreachable')} | Denied: {sum(1 for r in rows if r.status=='denied')}")
    else:
        print(f"\n{'Publisher':<12} {'Model ID':<42} {'Type':<15} {'Region':<14} {'Display Name'}")
        print("-" * 105)
        for r in rows:
            region = getattr(r, 'vertex_region', '') or '-'
            print(f"{r.publisher:<12} {r.model_id:<42} {r.model_type:<15} {region:<14} {r.display_name}")
        print(f"\nActive & callable: {len(rows)}")

    return rows


def get_token():
    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _try_anthropic(token, region, model_id, prompt):
    """Try Anthropic model via rawPredict."""
    url = (f"https://{region}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
           f"/locations/{region}/publishers/anthropic/models/{model_id}:rawPredict")
    payload = {
        "anthropic_version": "vertex-2023-10-16",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 50,
    }
    try:
        resp = http_requests.post(url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload, timeout=30)
        if resp.status_code == 200:
            text = resp.json().get("content", [{}])[0].get("text", "").strip()
            return text, region, model_id
        if resp.status_code != 404:
            err = resp.json().get("error", {}).get("message", "")[:120]
            return f"HTTP {resp.status_code}: {err}", region, model_id
    except Exception:
        pass
    return None, None, None


def _try_generate_content(token, region, publisher, model_id, prompt):
    url = (f"https://{region}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
           f"/locations/{region}/publishers/{publisher}/models/{model_id}:generateContent")
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    try:
        resp = http_requests.post(url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload, timeout=30)
        if resp.status_code == 200:
            text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            return text, region
        if resp.status_code != 404:
            return f"HTTP {resp.status_code}: {resp.text[:120]}", region
    except Exception as e:
        return f"ERROR: {e}", region
    return None, None


def test_models(rows, prompt="Say hello in 5 words"):
    token = get_token()
    results = []

    # Filter to only available models
    rows = [r for r in rows if r.is_available]

    print(f"\nPrompt: \"{prompt}\"")
    print(f"\n{'Status':<7} {'Publisher/Model':<55} {'Region':<14} {'Response'}")
    print("-" * 120)

    for r in rows:
        pub = r.publisher
        model = r.model_id
        # Use verified region from BQ first, then fallback to REGION_MAP
        verified_region = getattr(r, 'vertex_region', '') or ''
        regions = [verified_region] if verified_region else REGION_MAP.get(pub, ["us-central1"])

        text = None
        hit_region = None

        for region in regions:
            if pub == "anthropic":
                text, hit_region, _ = _try_anthropic(token, region, model, prompt)
            else:
                text, hit_region = _try_generate_content(token, region, pub, model, prompt)
            if text is not None:
                break

        ok = text and not text.startswith("HTTP") and not text.startswith("ERROR")
        status = "OK" if ok else "FAIL"
        display = f"\"{text[:60]}\"" if ok else (text or "not found in any region")

        print(f"  {status:<4} {pub}/{model:<50} {(hit_region or '-'):<14} {display}")
        results.append({"publisher": pub, "model_id": model, "ok": ok, "region": hit_region, "response": text})

    passed = sum(1 for r in results if r["ok"])
    print(f"\nResults: {passed}/{len(results)} passed")
    return results


def update_bq_status(results):
    client = bigquery.Client(project=PROJECT)
    now = datetime.now(timezone.utc).isoformat()
    for r in results:
        status = "verified" if r["ok"] else "unreachable"
        client.query(f"""
            UPDATE `{TABLE}`
            SET status = '{status}', checked_at = TIMESTAMP('{now}')
            WHERE publisher = '{r["publisher"]}' AND model_id = '{r["model_id"]}'
        """).result()
    print(f"\nUpdated {len(results)} rows in BigQuery")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test available Vertex AI models")
    parser.add_argument("--query", action="store_true", help="Show active models only (no API calls)")
    parser.add_argument("--all", action="store_true", help="Show all models including unreachable/denied")
    parser.add_argument("--prompt", default="Say hello in 5 words", help="Custom prompt to test")
    parser.add_argument("--publisher", help="Filter by publisher (google, anthropic, xai, meta)")
    parser.add_argument("--type", dest="model_type", help="Filter by type (reasoning, fast, balanced, open-source)")
    parser.add_argument("--update-status", action="store_true", help="Update BQ table with test results")
    args = parser.parse_args()

    show_all = args.all
    rows = query_available_models(publisher=args.publisher, model_type=args.model_type, show_all=show_all)

    if args.query or show_all:
        pass
    else:
        print("\n" + "=" * 120)
        print("TESTING API CALLS (active models only)...")
        print("=" * 120)
        results = test_models(rows, prompt=args.prompt)
        if args.update_status:
            update_bq_status(results)
