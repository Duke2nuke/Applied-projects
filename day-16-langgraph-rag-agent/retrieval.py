"""Stdlib-only TF-IDF retriever (the agent's RAG tool).

Same approach as Day 10's local RAG, rewritten here so this project is
self-contained: chunk-free short docs, TF-IDF vectors, cosine similarity.
No network, no API keys, no embeddings model.
"""

import json
import math
import os
import re
from collections import Counter

_DOCS_PATH = os.path.join(os.path.dirname(__file__), "docs.json")

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Common words carry no topical signal and inflate out-of-scope scores
# (e.g. "What is the capital of France?" matched on what/is/the/of).
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "what", "which", "who", "whom", "whose", "when",
    "where", "why", "how", "of", "to", "in", "on", "at", "for", "with",
    "by", "from", "and", "or", "but", "not", "no", "it", "its", "this",
    "that", "these", "those", "as", "i", "you", "he", "she", "we", "they",
    "my", "your", "his", "her", "our", "their", "me", "him", "us", "them",
    "can", "could", "should", "would", "will", "shall", "may", "might",
    "must", "have", "has", "had", "am", "if", "then", "than", "so", "such",
    "any", "some", "all", "each", "per", "about", "into", "over", "under",
    "after", "before", "between", "through", "during", "again", "once",
    "there", "here",
}


def tokenize(text):
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class Retriever:
    def __init__(self, docs):
        self.docs = docs
        self._idf = {}
        n = len(docs)
        df = Counter()
        self._tf = []
        for doc in docs:
            tokens = tokenize(doc["text"])
            counts = Counter(tokens)
            self._tf.append(counts)
            for tok in counts:
                df[tok] += 1
        for tok, count in df.items():
            self._idf[tok] = math.log((n + 1) / (count + 1)) + 1.0

    @classmethod
    def from_file(cls, path=_DOCS_PATH):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(data["docs"])

    def _vector(self, counts):
        vec = {}
        norm = 0.0
        for tok, count in counts.items():
            w = (1.0 + math.log(count)) * self._idf.get(tok, 0.0)
            vec[tok] = w
            norm += w * w
        return vec, math.sqrt(norm)

    def retrieve(self, query, top_k=3):
        """Return a list of {id, title, text, score} sorted by score desc."""
        q_counts = Counter(tokenize(query))
        q_vec, q_norm = self._vector(q_counts)
        results = []
        for doc, counts in zip(self.docs, self._tf):
            d_vec, d_norm = self._vector(counts)
            if q_norm == 0.0 or d_norm == 0.0:
                score = 0.0
            else:
                dot = sum(q_vec.get(t, 0.0) * d_vec.get(t, 0.0) for t in q_vec)
                score = dot / (q_norm * d_norm)
            results.append(
                {"id": doc["id"], "title": doc["title"], "text": doc["text"], "score": score}
            )
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]


def retrieve_docs(query, top_k=3):
    """Tool-shaped wrapper: the function the LangGraph agent calls."""
    return Retriever.from_file().retrieve(query, top_k=top_k)
