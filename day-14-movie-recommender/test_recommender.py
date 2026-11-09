"""Tests for the Day 14 movie recommender (stdlib unittest)."""

import unittest

from recommender import (
    MOVIES,
    evaluate,
    generate_ratings,
    global_mean,
    item_similarity,
    popularity,
    predict,
    recommend,
    train_test_split,
    user_means,
)


class TestRecommender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ratings, _ = generate_ratings()
        cls.train, cls.test = train_test_split(cls.ratings)
        cls.means = user_means(cls.train)
        cls.gmean = global_mean(cls.train)
        cls.sims = item_similarity(cls.train)

    def test_deterministic_data(self):
        again, _ = generate_ratings()
        self.assertEqual(again, self.ratings)

    def test_train_test_disjoint_and_complete(self):
        self.assertFalse(set(self.train) & set(self.test))
        self.assertEqual(len(self.train) + len(self.test), len(self.ratings))

    def test_similarity_symmetric_bounded_and_self_one(self):
        for (i, j), s in self.sims.items():
            self.assertEqual(self.sims[(j, i)], s)
            self.assertGreaterEqual(s, -1.0)
            self.assertLessEqual(s, 1.0)
        for m in range(len(MOVIES)):
            self.assertEqual(self.sims[(m, m)], 1.0)

    def test_predictions_in_range(self):
        for (u, m), _ in list(self.test.items())[:50]:
            p = predict(u, m, self.train, self.sims, self.means, self.gmean)
            self.assertGreaterEqual(p, 1.0)
            self.assertLessEqual(p, 5.0)

    def test_model_beats_global_mean_baseline(self):
        results = evaluate(self.train, self.test, self.sims, self.means,
                           self.gmean)
        self.assertLess(results["model_rmse"], results["global_mean_rmse"])
        self.assertLess(results["model_rmse"], results["user_mean_rmse"])

    def test_recommendations_exclude_rated_and_are_ranked(self):
        recs = recommend(0, self.train, self.sims, self.means, self.gmean)
        self.assertEqual(len(recs), 5)
        rated = {m for (u, m) in self.train if u == 0}
        self.assertFalse(any(m in rated for m, _ in recs))
        scores = [p for _, p in recs]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_cold_start_user_gets_popularity(self):
        new_user = 999  # never appears in training data
        self.assertAlmostEqual(
            predict(new_user, 0, self.train, self.sims, self.means, self.gmean),
            self.gmean,
        )
        pop = popularity(self.train)
        self.assertGreater(len(pop), 0)
        avgs = [a for _, a, _ in pop]
        self.assertEqual(avgs, sorted(avgs, reverse=True))
        self.assertTrue(all(c >= 5 for _, _, c in pop))


if __name__ == "__main__":
    unittest.main()
