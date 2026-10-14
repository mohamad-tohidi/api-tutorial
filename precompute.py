"""
Precompute answers for a list of questions, so users can vote on them later.

Usage:
    uv run precompute.py questions.txt [batch_size]

questions.txt has one question per line (default batch_size is 4).
Questions that are already in the database are skipped, so it is safe to re-run.
"""

import asyncio
import runpy
import sqlite3
import sys

import httpx

arena = runpy.run_path("api-tutorial.py")
ask_rag = arena["ask_rag"]
save_round = arena["save_round"]
API_A = arena["API_A"]
API_B = arena["API_B"]
DB_FILE = arena["DB_FILE"]
TIMEOUT = arena["TIMEOUT"]


def read_questions(path):
    with open(path, encoding="utf-8") as file:
        lines = file.read().splitlines()
    questions = [line.strip() for line in lines if line.strip()]
    return list(dict.fromkeys(questions))  # remove duplicates, keep order


def saved_questions():
    connection = sqlite3.connect(DB_FILE)
    rows = connection.execute("SELECT question FROM rounds").fetchall()
    connection.close()
    return {row[0] for row in rows}


async def compute(client, question):
    try:
        answer_a, answer_b = await asyncio.gather(
            ask_rag(client, API_A, question),
            ask_rag(client, API_B, question),
        )
    except Exception as error:
        print(f"skip: {question} ({error})")
        return
    save_round(question, answer_a, answer_b, precomputed=1)


async def main(path, batch_size):
    already_saved = saved_questions()
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
