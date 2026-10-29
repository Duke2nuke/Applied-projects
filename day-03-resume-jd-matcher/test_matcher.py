"""Tests for the resume-JD matcher.

Usage:
    python -m unittest test_matcher -v
"""

import unittest

from data import JOBS, SAMPLE_RESUME
from matcher import cosine_similarity, extract_skills, rank_jobs, tokenize, _tfidf_vectors


class TestMatcher(unittest.TestCase):
    def test_top_match_is_ml_intern(self):
        results = rank_jobs(SAMPLE_RESUME, JOBS)
        self.assertEqual(results[0]["id"], "ml-intern")
        self.assertEqual(len(results), len(JOBS))

    def test_scores_in_range_and_descending(self):
        results = rank_jobs(SAMPLE_RESUME, JOBS)
        scores = [r["score"] for r in results]
        self.assertTrue(all(0.0 <= s <= 1.0 for s in scores))
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_identical_text_scores_one(self):
        vec_a, vec_b = _tfidf_vectors(["python machine learning", "python machine learning"])
        self.assertAlmostEqual(cosine_similarity(vec_a, vec_b), 1.0, places=6)

    def test_empty_resume_scores_zero_without_crashing(self):
        results = rank_jobs("", JOBS)
        self.assertTrue(all(r["score"] == 0.0 for r in results))

    def test_skill_gap_spots_missing_deep_learning(self):
        results = rank_jobs(SAMPLE_RESUME, JOBS)
        top = results[0]
        self.assertIn("deep learning", top["missing_skills"])
        self.assertIn("python", top["matched_skills"])

    def test_stopwords_removed_from_tokens(self):
        self.assertNotIn("the", tokenize("the python and the sql"))


if __name__ == "__main__":
    unittest.main()
