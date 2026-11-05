import unittest
from pathlib import Path

from rag import TfIdfIndex, answer, chunk_text, evaluate, load_docs

HERE = Path(__file__).parent


class TestRag(unittest.TestCase):
    def setUp(self):
        self.index = TfIdfIndex(load_docs(HERE / "docs.json"))

    def test_chunking_overlap_advances(self):
        words = [f"w{i}" for i in range(100)]
        chunks = chunk_text(" ".join(words), size=40, overlap=10)
        self.assertTrue(all(len(c.split()) <= 40 for c in chunks))
        self.assertEqual(chunks[0].split()[-10:], chunks[1].split()[:10])

    def test_retrieval_finds_expected_doc(self):
        top = self.index.search("How does prompt caching reduce cost?", k=3)
        self.assertEqual(top[0]["doc_id"], "prompt-caching")

    def test_unrelated_question_is_refused(self):
        result = answer(self.index, "quantum chromodynamics lattice gauge theory", k=3)
        self.assertIsNone(result["answer"])
        self.assertIn("Not found", result["refusal"])

    def test_eval_runs_and_scores_are_in_range(self):
        metrics = evaluate(self.index, HERE / "eval.json", k=3)
        self.assertEqual(metrics["n"], 8)
        for key in ("recall@1", "recall@3", "mrr@3"):
            self.assertTrue(0.0 <= metrics[key] <= 1.0)


if __name__ == "__main__":
    unittest.main()
