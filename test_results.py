"""Self-check for vote counting. Run: uv run test_results.py"""

import runpy

app = runpy.run_path("api-tutorial.py")
count_votes = app["count_votes"]

rounds = {
    0: {"labels": ["api_a", "api_b"]},
    1: {"labels": ["api_b", "api_a"]},
    2: {"labels": ["api_a", "api_b"]},
    3: {"labels": ["api_a", "api_b"]},
}

votes = {
    0: "0",        # api_a wins
    1: "0",        # api_b wins
    2: "both",     # tie
    3: "neither",  # both lose
}

score = count_votes(rounds, votes)

assert score["api_a"] == {"wins": 1, "losses": 2, "ties": 1}, score["api_a"]
assert score["api_b"] == {"wins": 1, "losses": 2, "ties": 1}, score["api_b"]
print("ok")
