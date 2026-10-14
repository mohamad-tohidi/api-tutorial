"""Self-check for vote counting. Run: uv run test_db.py"""

import os
import tempfile

os.environ["DB_FILE"] = tempfile.mkdtemp() + "/test.db"

from db import count_votes

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

print("ok")
