"""Client for the two RAG streaming APIs."""

import json
import os

import httpx

PROJECT = "parsaqa"
API_A = os.getenv("RAG_API_A_URL", "http://localhost:8000")
API_B = os.getenv("RAG_API_B_URL", "http://localhost:8001")
TIMEOUT = httpx.Timeout(300, connect=10)


async def ask_rag(client, api_url, question):
    url = api_url + "/api/v1/chat/rag/stream"
    body = {"messages": [{"role": "user", "content": question}]}

    answer = ""
    async with client.stream("POST", url, params={"project_name": PROJECT}, json=body) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            event = json.loads(line.removeprefix("data:").strip())
            if event["state"] == "answering" and event["chunk"]:
                answer += event["chunk"]
            if event["done"]:
                break
    return answer
