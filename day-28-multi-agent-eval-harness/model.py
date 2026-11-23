"""Tiny local "model": a fact store plus keyword retrieval.

This is deliberately NOT a real LLM. It is a deterministic stand-in so
the harness can be run and tested with no API key, no downloads and no
GPU. The point of the project is the evaluation + tracing machinery
around the model, not the model itself. Any agent below only talks to
the ``Model`` interface (``retrieve`` / ``answer``), so a real LLM can
be dropped in later behind the same interface.
"""

import json
import re
from pathlib import Path

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "what", "which", "who",
    "whom", "whose", "when", "where", "why", "how", "does", "do", "did",
    "is", "and", "or", "but", "if", "then", "of", "on", "in", "at", "to",
    "for", "by", "with", "it", "its", "this", "that", "these", "those",
    "you", "your", "i", "me", "my", "we", "our", "they", "them", "their",
    "as", "from", "not", "no", "yes", "can", "could", "would", "should",
    "mean", "means", "does",
}
# Superlatives are terrible retrieval signals: every "largest X" fact
# matches every "largest Y" question. Content-word scoring drops them.
SUPERLATIVES = {"largest", "smallest", "hottest", "coldest", "biggest",
                 "most", "least", "best", "worst", "fastest", "slowest"}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def stem(token):
    """Very light stemming: strip a trailing 's' so rings ~ ring."""
    if len(token) > 3 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("es"):
        return token[:-2]
    if len(token) > 2 and token.endswith("s"):
        return token[:-1]
    return token


def tokenize(text):
    return [stem(t) for t in _TOKEN_RE.findall(text.lower())]


def content_words(text):
    """Question words that carry meaning: no stopwords, no superlatives."""
    return [t for t in tokenize(text)
            if t not in STOPWORDS and t not in SUPERLATIVES]


def estimate_tokens(text):
    """Rough token estimate (words x 1.3). Labelled as an estimate."""
    return max(1, round(len(text.split()) * 1.3))


class FactStore:
    def __init__(self, facts):
        self.facts = facts  # list of dicts: id, text, answer

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as fh:
            return cls(json.load(fh))

    def naive_retrieve(self, question):
        """Top-1 fact by distinct-token overlap, stopwords included.

        Deliberately naive: it counts every question word the same, so
        a distractor that shares the question's words (e.g. 'largest
        ocean' for 'largest planet') ties or beats the right fact.
        Ties break by store order, so a distractor listed first wins.
        """
        q_tokens = set(tokenize(question))
        best, best_score = None, -1
        for fact in self.facts:
            f_tokens = set(tokenize(fact["text"]))
            score = len(q_tokens & f_tokens)
            if score > best_score:
                best, best_score = fact, score
        return best, best_score

    def content_retrieve(self, question, extra_words=()):
        """Top-1 fact by content-word overlap, with two tie-breaks.

        Primary: distinct content words (no stopwords, no
        superlatives). Secondary: distinct superlatives from the
        question ('largest', 'hottest') — the words that say *which*
        extreme is wanted. Tertiary: shortest fact, i.e. the most
        specific statement. ``extra_words`` adds context, e.g. the
        answer to a previous sub-question, so 'its largest moon' can
        resolve 'its'.
        """
        words = set(content_words(question)) | {stem(w) for w in extra_words}
        superlatives = {t for t in tokenize(question) if t in SUPERLATIVES}
        best, best_key = None, None
        for fact in self.facts:
            f_tokens = set(tokenize(fact["text"]))
            key = (len(words & f_tokens),
                   len(superlatives & f_tokens),
                   -len(tokenize(fact["text"])))
            if best_key is None or key > best_key:
                best, best_key = fact, key
        return best, best_key[0]


class Model:
    """The stub 'model': answers a question from one retrieved fact."""

    def __init__(self, store):
        self.store = store

    def answer_from(self, fact):
        """Answer text is the fact itself, cited by id."""
        return f"{fact['text']} [{fact['id']}]"


def load_default_store():
    here = Path(__file__).parent
    return FactStore.load(here / "facts.json")
