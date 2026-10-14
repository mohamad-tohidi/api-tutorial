"""SQLite storage for rounds and votes."""

import os
import random
import sqlite3

DB_FILE = os.getenv("DB_FILE", "arena.db")


def connect():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def setup():
    connection = connect()
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER NOT NULL,
            choice TEXT NOT NULL
        );
    """)

    # old databases had one vote per round (round_id was the primary key)
    columns = [row["name"] for row in connection.execute("PRAGMA table_info(votes)")]
    if "id" not in columns:
        connection.executescript("""
            ALTER TABLE votes RENAME TO old_votes;
            CREATE TABLE votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id INTEGER NOT NULL,
                choice TEXT NOT NULL
            );
            INSERT INTO votes (round_id, choice) SELECT round_id, choice FROM old_votes;
            DROP TABLE old_votes;
        """)

    connection.commit()
    connection.close()


setup()


def save_round(question, answer_a, answer_b, precomputed):
    a_first = random.random() < 0.5
    connection = connect()
    cursor = connection.execute(
        "INSERT INTO rounds (question, answer_a, answer_b, a_first, precomputed) VALUES (?, ?, ?, ?, ?)",
        (question, answer_a, answer_b, a_first, precomputed),
    )
    round_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return round_id, a_first


def precomputed_count():
    connection = connect()
    count = connection.execute("SELECT COUNT(*) FROM rounds WHERE precomputed = 1").fetchone()[0]
    connection.close()
    return count


def round_at(index):
    connection = connect()
    row = connection.execute(
        "SELECT * FROM rounds WHERE precomputed = 1 ORDER BY id LIMIT 1 OFFSET ?",
        (index,),
    ).fetchone()
    connection.close()
    return row


def save_vote(round_id, choice):
    connection = connect()
    exists = connection.execute("SELECT 1 FROM rounds WHERE id = ?", (round_id,)).fetchone()
    if not exists:
        connection.close()
        return False

    connection.execute(
        "INSERT INTO votes (round_id, choice) VALUES (?, ?)",
        (round_id, choice),
    )
    connection.commit()
    connection.close()
    return True


def saved_questions():
    connection = connect()
    rows = connection.execute("SELECT question FROM rounds").fetchall()
    connection.close()
    return {row["question"] for row in rows}


def count_votes(votes):
    """votes is a list of (labels, choice); labels[0] was shown as answer 0."""
    score = {
        "api_a": {"wins": 0, "losses": 0, "ties": 0},
        "api_b": {"wins": 0, "losses": 0, "ties": 0},
    }

    for labels, choice in votes:
        first, second = labels

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


def results():
    connection = connect()
    rows = connection.execute("""
        SELECT rounds.a_first, votes.choice
        FROM votes
        JOIN rounds ON rounds.id = votes.round_id
    """).fetchall()
    total_rounds = precomputed_count()
    connection.close()

    votes = []
    for row in rows:
        labels = ["api_a", "api_b"] if row["a_first"] else ["api_b", "api_a"]
        votes.append((labels, row["choice"]))

    return {
        "rounds": total_rounds,
        "votes": len(votes),
        "score": count_votes(votes),
    }
