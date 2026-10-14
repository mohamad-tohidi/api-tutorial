"""
Compare two RAG APIs and vote on the better answer.

POST /ask      question -> two answers (ids 0 and 1)
POST /vote     pick 0, 1, both or neither
GET  /results  show the scores

The two RAG endpoints come from RAG_API_A_URL and RAG_API_B_URL.
Records are saved as one JSON object per line in data.txt.
"""

import asyncio
import json
import os
import random
from pathlib import Path
from typing import Literal

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

PROJECT = "parsaqa"
API_A = os.getenv("RAG_API_A_URL", "http://localhost:8001")
API_B = os.getenv("RAG_API_B_URL", "http://localhost:8002")
DATA_FILE = Path("data.txt")
TIMEOUT = httpx.Timeout(300, connect=10)

app = FastAPI()


def read_records():
    if not DATA_FILE.exists():
        return []
    lines = DATA_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def write_record(record):
    with DATA_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


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


async def safe_ask(client, api_url, question):
    try:
        return await ask_rag(client, api_url, question)
    except Exception as error:
        return f"[{api_url} error: {error}]"


class AskRequest(BaseModel):
    question: str


class VoteRequest(BaseModel):
    id: int
    choice: Literal["0", "1", "both", "neither"]


@app.post("/ask")
async def ask(payload: AskRequest):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        answer_a, answer_b = await asyncio.gather(
            safe_ask(client, API_A, payload.question),
            safe_ask(client, API_B, payload.question),
        )

    # randomly put the two APIs in slot 0 and slot 1, so the vote is blind
    labeled = [("api_a", answer_a), ("api_b", answer_b)]
    random.shuffle(labeled)
    labels = [name for name, _ in labeled]
    answers = [text for _, text in labeled]

    round_id = sum(1 for record in read_records() if record["type"] == "round")
    write_record({
        "type": "round",
        "id": round_id,
        "question": payload.question,
        "labels": labels,
        "answers": answers,
    })

    return {
        "id": round_id,
        "answers": [
            {"id": 0, "text": answers[0]},
            {"id": 1, "text": answers[1]},
        ],
    }


@app.post("/vote")
async def vote(payload: VoteRequest):
    for record in read_records():
        if record["type"] == "round" and record["id"] == payload.id:
            write_record({"type": "vote", "id": payload.id, "choice": payload.choice})
            return {"ok": True}
    raise HTTPException(404, "round not found")


def count_votes(rounds, votes):
    score = {
        "api_a": {"wins": 0, "losses": 0, "ties": 0},
        "api_b": {"wins": 0, "losses": 0, "ties": 0},
    }

    for round_id in votes:
        choice = votes[round_id]
        first = rounds[round_id]["labels"][0]
        second = rounds[round_id]["labels"][1]

        if choice == "both":
            score[first]["ties"] += 1
            score[second]["ties"] += 1
        elif choice == "neither":
            score[first]["losses"] += 1
            score[second]["losses"] += 1
        elif choice == "0":
            score[first]["wins"] += 1
            score[second]["losses"] += 1
        else:
            score[second]["wins"] += 1
            score[first]["losses"] += 1

    return score


@app.get("/results")
async def results():
    rounds = {}
    votes = {}
    for record in read_records():
        if record["type"] == "round":
            rounds[record["id"]] = record
        elif record["type"] == "vote":
            votes[record["id"]] = record["choice"]

    return {
        "rounds": len(rounds),
        "votes": len(votes),
        "score": count_votes(rounds, votes),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
