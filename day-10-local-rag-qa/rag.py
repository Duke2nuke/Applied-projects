"""Local, stdlib-only RAG: chunk -> TF-IDF retrieve -> grounded answer.

No LLM, no API key, no downloads. The "answer" is the retrieved
passage itself, with its source id and score. If nothing scores
above the threshold, the system says it does not know instead of
inventing an answer. That refusal is a feature, not a bug: it is
the grounding check a real RAG system needs before any generation
step is added on top.
"""
import json
import math
import re
from pathlib import Path

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return TOKEN_RE.findall(text.lower())


def chunk_text(text, size=40, overlap=10):
    """Split text into word windows of `size` words, overlapping by `overlap`."""
    words = text.split()
    if not words:
        return []
    if len(words) <= size:
        return [" ".join(words)]
    chunks, start = [], 0
    step = max(1, size - overlap)
    while start < len(words):
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
        start += step
    return chunks


def load_docs(docs_path):
    """Load docs.json: list of {id, title, text}. Returns list of chunk dicts."""
    docs = json.loads(Path(docs_path).read_text())
    chunks = []
    for doc in docs:
        for i, chunk in enumerate(chunk_text(doc["text"])):
            chunks.append({"doc_id": doc["id"], "title": doc["title"],
                           "chunk_id": f"{doc['id']}#c{i}", "text": chunk})
    return chunks


class TfIdfIndex:
    def __init__(self, chunks):
        self.chunks = chunks
        self.n = len(chunks)
        self.df = {}
        self.doc_tokens = []
        for chunk in chunks:
            tokens = tokenize(chunk["text"])
            self.doc_tokens.append(tokens)
            for term in set(tokens):
                self.df[term] = self.df.get(term, 0) + 1
        self.idf = {t: math.log((1 + self.n) / (1 + df)) + 1.0
                    for t, df in self.df.items()}

    def _vector(self, tokens):
        counts = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        vec = {}
        for term, count in counts.items():
            if term in self.idf:
                vec[term] = (1 + math.log(count)) * self.idf[term]
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, query, k=3):
        qvec = self._vector(tokenize(query))
        scored = []
        for chunk, tokens in zip(self.chunks, self.doc_tokens):
            dvec = self._vector(tokens)
            score = sum(qvec[t] * dvec.get(t, 0.0) for t in qvec)
            scored.append((score, chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [{"score": round(score, 4), **chunk}
                for score, chunk in scored[:k] if score > 0]


def answer(index, query, k=3, threshold=0.15):
    """Return top-k passages, or a refusal when nothing is grounded."""
    results = index.search(query, k=k)
    if not results or results[0]["score"] < threshold:
        return {"query": query, "answer": None,
                "refusal": "Not found in the provided documents.",
                "sources": []}
    return {"query": query,
            "answer": results[0]["text"],
            "sources": [{"doc_id": r["doc_id"], "chunk_id": r["chunk_id"],
                         "score": r["score"]} for r in results]}


def evaluate(index, eval_path, k=3):
    """Recall@1, Recall@k and MRR over a golden Q&A set.

    eval file: list of {question, expected_doc_id}.
    """
    cases = json.loads(Path(eval_path).read_text())
    hits_at_1 = hits_at_k = reciprocal_sum = 0
    details = []
    for case in cases:
        results = index.search(case["question"], k=k)
        ids = [r["doc_id"] for r in results]
        rank = ids.index(case["expected_doc_id"]) + 1 if case["expected_doc_id"] in ids else None
        if rank == 1:
            hits_at_1 += 1
        if rank is not None:
            hits_at_k += 1
            reciprocal_sum += 1.0 / rank
        details.append({**case, "rank": rank,
                        "top_doc": ids[0] if ids else None})
    n = len(cases) or 1
    return {"n": len(cases), "recall@1": round(hits_at_1 / n, 3),
            "recall@%d" % k: round(hits_at_k / n, 3),
            "mrr@%d" % k: round(reciprocal_sum / n, 3),
            "details": details}
