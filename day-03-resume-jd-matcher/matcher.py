"""Resume-to-job-description matcher: TF-IDF + cosine similarity, plus
a skill-gap check. Standard library only — the TF-IDF is implemented
by hand so there is nothing to install.

Why ranking instead of classification: a resume is not "in" or "out"
for one role; the useful question is *which* of many postings fits
best, and *what is missing* for the top ones. That is a retrieval
problem, so cosine similarity over TF-IDF vectors is the natural
first tool — the same idea behind simple search engines.

Usage:
    from matcher import rank_jobs
    results = rank_jobs(resume_text, jobs)
"""

import math
import re
from collections import Counter

# Small stopword list: words that appear everywhere and carry no
# matching signal. Kept short on purpose — over-aggressive stopword
# removal can delete meaningful terms in short texts like resumes.
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "with",
    "on", "is", "are", "you", "will", "this", "that", "by", "as",
    "at", "from", "we", "our", "your", "its", "it", "be", "no",
}

# Skill vocabulary for the gap analysis. A skill counts as "present"
# when its phrase appears in the text (case-insensitive, hyphens
# treated as spaces, so "scikit-learn" matches "scikit learn").
SKILLS = [
    "python", "sql", "pandas", "numpy", "scikit-learn", "tensorflow",
    "pytorch", "machine learning", "deep learning", "nlp",
    "natural language processing", "computer vision",
    "data analysis", "data visualization", "matplotlib", "statistics",
    "git", "docker", "kubernetes", "aws", "react", "javascript",
    "typescript", "html", "css", "node.js", "flask", "fastapi",
    "django", "java", "c++", "linux", "spark", "tableau", "excel",
    "rest api", "postgresql", "mongodb",
]


def _normalize(text):
    """Lowercase and turn hyphens into spaces for phrase matching."""
    return re.sub(r"[-_]", " ", text.lower())


def tokenize(text):
    """Lowercase word tokens, minus stopwords. Keeps 'c++' style tokens out
    of the TF-IDF vocabulary (they are handled by skill matching instead)."""
    tokens = re.findall(r"[a-z][a-z0-9]*", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def _tfidf_vectors(documents):
    """Return L2-normalised TF-IDF vectors (dicts) for each document.

    IDF uses add-one smoothing: log((1 + N) / (1 + df)) + 1, so a term
    appearing in every document still gets a small positive weight
    instead of zero — important for short texts, where a shared core
    term like 'python' should still count for something.
    """
    tokenized = [tokenize(doc) for doc in documents]
    n_docs = len(documents)
    doc_freq = Counter()
    for tokens in tokenized:
        doc_freq.update(set(tokens))

    vectors = []
    for tokens in tokenized:
        counts = Counter(tokens)
        total = len(tokens) or 1
        vec = {}
        for term, count in counts.items():
            tf = count / total
            idf = math.log((1 + n_docs) / (1 + doc_freq[term])) + 1
            vec[term] = tf * idf
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({term: v / norm for term, v in vec.items()})
    return vectors


def cosine_similarity(vec_a, vec_b):
    """Cosine similarity of two L2-normalised sparse vectors."""
    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) > len(vec_b):
        vec_a, vec_b = vec_b, vec_a
    return sum(value * vec_b.get(term, 0.0) for term, value in vec_a.items())


def extract_skills(text):
    """Skills from SKILLS whose phrase appears in the text."""
    normalized = _normalize(text)
    raw = text.lower()
    found = set()
    for skill in SKILLS:
        if skill == "c++":
            if "c++" in raw:
                found.add(skill)
        elif _normalize(skill) in normalized:
            found.add(skill)
    return found


def rank_jobs(resume_text, jobs):
    """Rank jobs by cosine similarity to the resume.

    Returns a list of dicts, best first, each with: the job's id/title/
    company, score (0-1), matched_skills (in both resume and JD) and
    missing_skills (required by the JD, absent from the resume).
    """
    documents = [resume_text] + [job["description"] for job in jobs]
    vectors = _tfidf_vectors(documents)
    resume_vec = vectors[0]
    resume_skills = extract_skills(resume_text)

    results = []
    for job, vec in zip(jobs, vectors[1:]):
        job_skills = extract_skills(job["description"])
        results.append({
            "id": job["id"],
            "title": job["title"],
            "company": job["company"],
            "score": round(cosine_similarity(resume_vec, vec), 4),
            "matched_skills": sorted(resume_skills & job_skills),
            "missing_skills": sorted(job_skills - resume_skills),
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results
