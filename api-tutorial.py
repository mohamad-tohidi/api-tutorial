"""
Compare two RAG APIs and vote on the better answer.

Live:        POST /ask      question -> two answers (ids 0 and 1)
Precomputed: GET /question  next unvoted precomputed question
Vote:        POST /vote     pick 0, 1, both or neither
Results:     GET /results   show the scores

The two RAG endpoints come from RAG_API_A_URL and RAG_API_B_URL.
Everything is stored in a SQLite database (arena.db).
"""

import asyncio
import json
import os
import random
import sqlite3
from typing import Literal

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

PROJECT = "parsaqa"
API_A = os.getenv("RAG_API_A_URL", "http://localhost:8001")
API_B = os.getenv("RAG_API_B_URL", "http://localhost:8002")
DB_FILE = os.getenv("DB_FILE", "arena.db")
TIMEOUT = httpx.Timeout(300, connect=10)

app = FastAPI()


def connect_db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def setup_db():
    connection = connect_db()
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer_a TEXT NOT NULL,
            answer_b TEXT NOT NULL,
            a_first INTEGER NOT NULL,
            precomputed INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS votes (
            round_id INTEGER PRIMARY KEY,
            choice TEXT NOT NULL
        );
    """)
    connection.commit()
    connection.close()


setup_db()


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


def save_round(question, answer_a, answer_b, precomputed):
    a_first = random.random() < 0.5
    connection = connect_db()
    cursor = connection.execute(
        "INSERT INTO rounds (question, answer_a, answer_b, a_first, precomputed) VALUES (?, ?, ?, ?, ?)",
        (question, answer_a, answer_b, a_first, precomputed),
    )
    round_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return round_id, a_first


def blind_answers(a_first, answer_a, answer_b):
    if a_first:
        ordered = [answer_a, answer_b]
    else:
        ordered = [answer_b, answer_a]
    return [
        {"id": 0, "text": ordered[0]},
        {"id": 1, "text": ordered[1]},
    ]


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

    round_id, a_first = save_round(payload.question, answer_a, answer_b, precomputed=0)
    return {
        "id": round_id,
        "question": payload.question,
        "answers": blind_answers(a_first, answer_a, answer_b),
    }


@app.get("/question")
async def question():
    connection = connect_db()
    row = connection.execute("""
        SELECT * FROM rounds
        WHERE precomputed = 1
          AND id NOT IN (SELECT round_id FROM votes)
        ORDER BY RANDOM()
        LIMIT 1
    """).fetchone()
    connection.close()

    if row is None:
        raise HTTPException(404, "no precomputed question left")

    return {
        "id": row["id"],
        "question": row["question"],
        "answers": blind_answers(row["a_first"], row["answer_a"], row["answer_b"]),
    }


@app.post("/vote")
async def vote(payload: VoteRequest):
    connection = connect_db()
    exists = connection.execute("SELECT 1 FROM rounds WHERE id = ?", (payload.id,)).fetchone()
    if not exists:
        connection.close()
        raise HTTPException(404, "round not found")

    connection.execute(
        "INSERT OR REPLACE INTO votes (round_id, choice) VALUES (?, ?)",
        (payload.id, payload.choice),
    )
    connection.commit()
    connection.close()
    return {"ok": True}


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
    connection = connect_db()
    rows = connection.execute("""
        SELECT rounds.id, rounds.a_first, votes.choice
        FROM votes
        JOIN rounds ON rounds.id = votes.round_id
    """).fetchall()
    total_rounds = connection.execute("SELECT COUNT(*) FROM rounds").fetchone()[0]
    connection.close()

    rounds = {}
    votes = {}
    for row in rows:
        labels = ["api_a", "api_b"] if row["a_first"] else ["api_b", "api_a"]
        rounds[row["id"]] = {"labels": labels}
        votes[row["id"]] = row["choice"]

    return {
        "rounds": total_rounds,
        "votes": len(votes),
        "score": count_votes(rounds, votes),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
