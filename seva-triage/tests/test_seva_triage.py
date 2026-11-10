"""Tests for seva-triage: classifier, urgency rules, and the Flask API.

Classifier test sentences are paraphrases NOT in data.py, so they test
generalisation, not memorisation.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app
from data import DATA
from model import predict, train_full
from urgency import urgency

MODEL = train_full()


class TestClassifier(unittest.TestCase):
    def test_water_paraphrase(self):
        dept, conf = predict(MODEL, "The taps in our house have been dry since Monday")
        self.assertEqual(dept, "Water Supply")
        # Short ambiguous sentence: correct label, modest confidence.
        self.assertGreater(conf, 0.2)

    def test_electricity_paraphrase(self):
        dept, _ = predict(MODEL, "Our street has had no power since the storm last night")
        self.assertEqual(dept, "Electricity")

    def test_roads_paraphrase(self):
        dept, _ = predict(MODEL, "The main road near the market is full of deep potholes")
        self.assertEqual(dept, "Roads & Transport")

    def test_health_paraphrase(self):
        dept, _ = predict(MODEL, "The clinic in our area has run out of fever medicine")
        self.assertEqual(dept, "Health")

    def test_education_paraphrase(self):
        dept, _ = predict(MODEL, "The primary school has no maths teacher this term")
        self.assertEqual(dept, "Education")

    def test_revenue_paraphrase(self):
        dept, _ = predict(MODEL, "My caste certificate request has been waiting for months")
        self.assertEqual(dept, "Revenue & Certificates")


class TestUrgency(unittest.TestCase):
    def test_high_burst_pipe(self):
        self.assertEqual(urgency("A pipeline burst and sewage is flooding the street"), "high")

    def test_high_ambulance(self):
        self.assertEqual(urgency("My father needs an ambulance, the hospital is not answering"), "high")

    def test_medium_pending_certificate(self):
        self.assertEqual(urgency("My income certificate has been pending for two months"), "medium")

    def test_low_routine(self):
        self.assertEqual(urgency("The street light outside my house flickers sometimes"), "low")


class TestApi(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health(self):
        self.assertEqual(self.client.get("/health").get_json(), {"status": "ok"})

    def test_triage_returns_all_fields(self):
        resp = self.client.post("/triage", json={"text": "There is no water supply in our street"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["department"], "Water Supply")
        self.assertEqual(body["urgency"], "low")
        self.assertIn("confidence", body)
        self.assertIn("suggested_next_step", body)

    def test_triage_high_urgency(self):
        resp = self.client.post(
            "/triage", json={"text": "No water for three days, children are falling sick"}
        )
        self.assertEqual(resp.get_json()["urgency"], "high")

    def test_triage_empty_text_400(self):
        self.assertEqual(self.client.post("/triage", json={"text": "  "}).status_code, 400)

    def test_analytics_counts(self):
        body = self.client.get("/analytics").get_json()
        self.assertEqual(body["total_grievances"], len(DATA))
        self.assertEqual(sum(body["department_counts"].values()), len(DATA))
        self.assertEqual(len(body["department_counts"]), 6)
        self.assertEqual(
            sum(body["urgency_breakdown"].values()), len(DATA)
        )


if __name__ == "__main__":
    unittest.main()
