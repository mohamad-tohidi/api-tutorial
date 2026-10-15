"""Self-check for vote counting. Run: uv run test_db.py"""

import os
import sqlite3
import tempfile

os.environ["DB_FILE"] = tempfile.mkdtemp() + "/test.db"

# an old-schema db (round_id primary key, no voter column) must migrate in setup()
connection = sqlite3.connect(os.environ["DB_FILE"])
connection.executescript("""
    CREATE TABLE votes (round_id INTEGER PRIMARY KEY, choice TEXT NOT NULL);
    INSERT INTO votes (round_id, choice) VALUES (1, 'both');
""")
connection.commit()
connection.close()

from db import BUNDLE, count_votes

# quick sanity on the bundle path used for static/ and the embedded arena.db
assert BUNDLE.is_dir(), BUNDLE

votes = [
    (["api_a", "api_b"], "0"),        # api_a wins
    (["api_b", "api_a"], "0"),        # api_b wins
    (["api_a", "api_b"], "both"),     # tie
    (["api_a", "api_b"], "neither"),  # both lose
]

score = count_votes(votes)

assert score["api_a"] == {"wins": 1, "losses": 2, "ties": 1}, score["api_a"]
assert score["api_b"] == {"wins": 1, "losses": 2, "ties": 1}, score["api_b"]

# two users voting on the same round must both count
same_round = [(["api_a", "api_b"], "0"), (["api_a", "api_b"], "0")]
assert count_votes(same_round)["api_a"]["wins"] == 2, count_votes(same_round)

# the old-schema row survived migration and gained the voter column
rows = sqlite3.connect(os.environ["DB_FILE"]).execute(
    "SELECT round_id, choice, voter FROM votes"
).fetchall()
assert rows == [(1, "both", "")], rows

print("ok")
