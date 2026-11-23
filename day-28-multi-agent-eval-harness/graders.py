"""Deterministic graders: no LLM judge, just string checks.

- correctness: fraction of the gold keywords present in the answer
  (substring match, case-insensitive).
- grounded: 1.0 if every cited fact id is in the gold supporting set,
  else 0.0. A right-sounding answer cited to the wrong fact fails.
- concise: 1.0 if the answer is at most 40 words, else 0.0.
"""

MAX_WORDS = 40


def grade(result, case):
    answer = result.answer.lower()
    hits = sum(1 for kw in case["keywords"] if kw.lower() in answer)
    correctness = hits / len(case["keywords"]) if case["keywords"] else 0.0
    grounded = 1.0 if (result.cited
                       and all(c in case["supporting"] for c in result.cited)
                       ) else 0.0
    concise = 1.0 if len(result.answer.split()) <= MAX_WORDS else 0.0
    return {
        "correctness": round(correctness, 3),
        "grounded": grounded,
        "concise": concise,
    }


def mean(scores, key):
    vals = [s[key] for s in scores]
    return round(sum(vals) / len(vals), 3) if vals else 0.0
