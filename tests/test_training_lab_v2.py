import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from training_lab_v2 import (  # noqa: E402
    SEED,
    SYNTHETIC_TEST_ROWS,
    SYNTHETIC_TRAIN_ROWS,
    get_model_benchmark_v2_payload,
    get_model_card_payload,
    get_training_lab_payload,
)


class TrainingLabV2Tests(unittest.TestCase):
    def test_training_lab_payload_shape_and_synthetic_scope(self):
        payload = get_training_lab_payload()

        self.assertEqual(payload["dataset"]["seed"], SEED)
        self.assertEqual(payload["dataset"]["syntheticTrainRows"], SYNTHETIC_TRAIN_ROWS)
        self.assertEqual(payload["dataset"]["syntheticTestRows"], SYNTHETIC_TEST_ROWS)
        self.assertEqual(payload["claimsBoundary"]["dataScope"], "deterministic synthetic sensor windows only")
        self.assertTrue(payload["model"]["advisoryUseOnly"])

    def test_sers_synthetic_scorer_beats_simple_baselines_on_accuracy(self):
        benchmark = get_model_benchmark_v2_payload()
        self.assertTrue(benchmark["sersBeatsAllBaselinesOnAccuracy"])

        metrics = benchmark["metrics"]
        sers_accuracy = metrics["SERS synthetic scorer"]["accuracy"]
        baseline_accuracies = [
            value["accuracy"]
            for key, value in metrics.items()
            if key != "SERS synthetic scorer"
        ]
        self.assertGreater(sers_accuracy, max(baseline_accuracies))

    def test_required_metrics_exist(self):
        benchmark = get_model_benchmark_v2_payload()

        for name, metric in benchmark["metrics"].items():
            with self.subTest(name=name):
                self.assertIn("accuracy", metric)
                self.assertIn("precision", metric)
                self.assertIn("recall", metric)
                self.assertIn("falsePositives", metric)
                self.assertIn("falseNegatives", metric)
                self.assertIn("confusionMatrix", metric)

    def test_model_card_claim_boundary_has_no_forbidden_autonomous_claims(self):
        text = json.dumps(
            {
                "trainingLab": get_training_lab_payload(),
                "benchmark": get_model_benchmark_v2_payload(),
                "modelCard": get_model_card_payload(),
            },
            sort_keys=True,
        ).lower()

        forbidden_terms = [
            "safe_for_distribution",
            "automatic release",
            "automatic quarantine",
            "automatic discard",
            "automatic reroute",
            "automatic customer notification",
            "autonomous release",
            "autonomous quarantine",
            "autonomous discard",
            "autonomous reroute",
            "production validated",
            "pharma validated",
            "real-world validated",
            "competitor",
            "competitors",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, text)


if __name__ == "__main__":
    unittest.main()