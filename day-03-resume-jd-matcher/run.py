"""End-to-end demo: rank synthetic job postings against a synthetic
sample resume, and show the skill gaps for the top match.

Usage:
    python run.py
"""

from data import JOBS, SAMPLE_RESUME
from matcher import rank_jobs


def main():
    results = rank_jobs(SAMPLE_RESUME, JOBS)
    print("Resume -> job ranking (TF-IDF cosine similarity, 0-1):\n")
    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. {result['title']} @ {result['company']} "
            f"— score {result['score']:.4f}"
        )
        print(f"   matched skills: {', '.join(result['matched_skills']) or 'none'}")
        print(f"   missing skills: {', '.join(result['missing_skills']) or 'none'}")
    top = results[0]
    print(
        f"\nTop match: {top['title']} @ {top['company']}. "
        f"To strengthen this application, the gaps to close are: "
        f"{', '.join(top['missing_skills']) or 'none'}."
    )


if __name__ == "__main__":
    main()
