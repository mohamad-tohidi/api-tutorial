"""Precompute answers for questions listed in a text file.

Usage:
    uv run precompute.py questions.txt [batch_size]

Questions already in the database are skipped, so it is safe to re-run.
"""

import asyncio
import sys

import httpx

import db
from rag import API_A, API_B, TIMEOUT, ask_rag


def read_questions(path):
    with open(path, encoding="utf-8") as file:
        lines = file.read().splitlines()
    questions = [line.strip() for line in lines if line.strip()]
    return list(dict.fromkeys(questions))  # remove duplicates, keep order


async def compute(client, question):
    try:
        answer_a, answer_b = await asyncio.gather(
            ask_rag(client, API_A, question),
            ask_rag(client, API_B, question),
        )
    except Exception as error:
        print(f"skip: {question} ({error})")
        return
    db.save_round(question, answer_a, answer_b, precomputed=1)


async def main(path, batch_size):
    already_saved = db.saved_questions()
    questions = [question for question in read_questions(path) if question not in already_saved]
    print(f"{len(questions)} new questions")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for start in range(0, len(questions), batch_size):
            batch = questions[start : start + batch_size]
            await asyncio.gather(*[compute(client, question) for question in batch])
            done = min(start + batch_size, len(questions))
            print(f"saved {done}/{len(questions)}")


if __name__ == "__main__":
    questions_file = sys.argv[1]
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    asyncio.run(main(questions_file, batch_size))
