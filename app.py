"""RAG arena API.

GET  /question?index=0  one precomputed question with its two answers
POST /vote              pick 0, 1, both or neither
GET  /results           scores for api_a and api_b
"""

from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db

app = FastAPI(title="RAG Arena")


def blind_answers(a_first, answer_a, answer_b):
    if a_first:
        ordered = [answer_a, answer_b]
    else:
        ordered = [answer_b, answer_a]
    return [
        {"id": 0, "text": ordered[0]},
        {"id": 1, "text": ordered[1]},
    ]


class VoteRequest(BaseModel):
    id: int
    choice: Literal["0", "1", "both", "neither"]


@app.get("/question")
async def question(index: int = 0):
    total = db.precomputed_count()
    if index < 0 or index >= total:
        raise HTTPException(404, "no precomputed question left")

    row = db.round_at(index)
    return {
        "index": index,
        "total": total,
        "id": row["id"],
        "question": row["question"],
        "answers": blind_answers(row["a_first"], row["answer_a"], row["answer_b"]),
    }


@app.post("/vote")
async def vote(payload: VoteRequest):
    if not db.save_vote(payload.id, payload.choice):
        raise HTTPException(404, "round not found")
    return {"ok": True}


@app.get("/results")
async def results():
    return db.results()


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
