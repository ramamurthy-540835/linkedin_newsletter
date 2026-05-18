from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import subprocess
import requests
import uuid
import time
import traceback

PROJECT = "ctoteam"
MODEL = "claude-opus-4-6"
URL = (
    f"https://aiplatform.googleapis.com/v1/"
    f"projects/{PROJECT}/locations/global/"
    f"publishers/anthropic/models/{MODEL}:rawPredict"
)

app = FastAPI()


def get_token():
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            text=True
        ).strip()
        return token
    except Exception as e:
        print("TOKEN ERROR:", str(e))
        raise


@app.get("/health")
def health():
    return {
        "status": "ok",
        "project": PROJECT,
        "model": MODEL,
        "endpoint": URL
    }


@app.post("/v1/chat/completions")
async def chat(req: Request):
    try:
        body = await req.json()
        messages = body.get("messages", [])
        max_tokens = body.get("max_tokens", 4096)

        payload = {
            "anthropic_version": "vertex-2023-10-16",
            "max_tokens": max_tokens,
            "messages": messages
        }

        print("=" * 80)
        print("REQUEST TO VERTEX")
        print("MODEL:", MODEL)
        print("MESSAGE COUNT:", len(messages))

        token = get_token()

        response = requests.post(
            URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            },
            json=payload,
            timeout=300
        )

        print("VERTEX STATUS:", response.status_code)

        if response.status_code >= 400:
            print("VERTEX ERROR:", response.text)
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )

        data = response.json()

        print("VERTEX_UPSTREAM_MODEL:", data.get("model"))
        print("VERTEX_UPSTREAM_ID:", data.get("id"))

        text = ""
        for item in data.get("content", []):
            if item.get("type") == "text":
                text += item.get("text", "")

        return {
            "id": "chatcmpl-" + uuid.uuid4().hex,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": data.get("model", MODEL),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": data.get("usage", {})
        }

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
