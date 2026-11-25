import json
import unittest
from pathlib import Path

from sentiment import DATA_DIR, evaluate, load_data, predict_text, train

HERE = Path(__file__).resolve().parent


class TestLoadData(unittest.TestCase):
    def test_3000_rows_three_sources(self):
        rows = load_data()
        self.assertEqual(len(rows), 3000)
        for source in ("amazon", "imdb", "yelp"):
            self.assertEqual(
                sum(1 for r in rows if r["source"] == source), 1000
            )

    def test_labels_binary_and_roughly_balanced(self):
        rows = load_data()
        self.assertTrue(all(r["label"] in (0, 1) for r in rows))
        n_pos = sum(r["label"] for r in rows)
        self.assertGreater(n_pos, 1200)
        self.assertLess(n_pos, 1800)

    def test_no_empty_text(self):
        rows = load_data()
        self.assertTrue(all(r["text"].strip() for r in rows))


class TestEvaluate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_data()
        cls.results = evaluate(cls.rows)

    def test_split_sizes(self):
        self.assertEqual(self.results["n_train"], 2400)
        self.assertEqual(self.results["n_test"], 600)

    def test_logreg_beats_baseline(self):
        # Majority-class baseline is ~0.5; 0.80 leaves margin under the
        # measured 0.835.
        m = self.results["models"]["logreg"]
        self.assertGreater(m["accuracy"], 0.80)
        self.assertGreater(m["macro_f1"], 0.80)

    def test_nb_beats_baseline(self):
        m = self.results["models"]["nb"]
        self.assertGreater(m["accuracy"], 0.75)

    def test_logreg_beats_nb(self):
        self.assertGreater(
            self.results["models"]["logreg"]["accuracy"],
            self.results["models"]["nb"]["accuracy"],
        )

    def test_per_source_accuracy_floor(self):
        for name, m in self.results["models"].items():
            for source, acc in m["per_source_accuracy"].items():
                self.assertGreater(acc, 0.70, f"{name}/{source}")

    def test_confusion_matrix_sums_to_test_size(self):
        for m in self.results["models"].values():
            total = sum(sum(row) for row in m["confusion_matrix"])
            self.assertEqual(total, 600)


class TestPredict(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_data()
        cls.vectorizer, cls.model = train(cls.rows, "logreg")

    def test_known_positive_sentence(self):
        # Sentence taken from the training file itself.
        out = predict_text(self.vectorizer, self.model,
                            "Good case, Excellent value.")
        self.assertEqual(out["label"], 1)
        self.assertGreater(out["probability"], 0.5)

    def test_known_negative_sentence(self):
        out = predict_text(
            self.vectorizer, self.model,
            "Tied to charger for conversations lasting more than 45 minutes."
            "MAJOR PROBLEMS!!",
        )
        self.assertEqual(out["label"], 0)

    def test_fresh_sentences_sane(self):
        for text in ("I love this, it works great",
                     "Terrible, broke after one day"):
            out = predict_text(self.vectorizer, self.model, text)
            self.assertIn(out["label"], (0, 1))
            self.assertGreaterEqual(out["probability"], 0.5)
            self.assertLessEqual(out["probability"], 1.0)

    def test_empty_input_rejected(self):
        with self.assertRaises(ValueError):
            predict_text(self.vectorizer, self.model, "   ")


class TestMetricsFile(unittest.TestCase):
    def test_metrics_json_matches_evaluate(self):
        metrics = json.loads((HERE / "metrics.json").read_text())
        self.assertEqual(metrics["n_test"], 600)
        self.assertAlmostEqual(
            metrics["models"]["logreg"]["accuracy"], 0.835, places=3
        )
        self.assertAlmostEqual(
            metrics["models"]["nb"]["accuracy"], 0.8017, places=3
        )


if __name__ == "__main__":
    unittest.main()
