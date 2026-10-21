"""Offline release checks using only invented inputs."""

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_demo
import scoring


def isolated_project(directory):
    root = Path(directory)
    (root / "scripts").mkdir()
    (root / "data").mkdir()
    for name in ("scoring.py", "generate_demo.py"):
        shutil.copyfile(ROOT / "scripts" / name, root / "scripts" / name)
    return root


class DemoTests(unittest.TestCase):
    def test_fixtures_are_reproducible_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = isolated_project(directory)
            command = [sys.executable, str(root / "scripts" / "generate_demo.py")]
            for _ in range(2):
                subprocess.run(command, cwd=root / "data", check=True, capture_output=True)
                for name in ("latest.json", "history.json"):
                    self.assertEqual((root / "data" / name).read_bytes(), (ROOT / "data" / name).read_bytes())
            subprocess.run(command + ["--check"], cwd=root / "data", check=True, capture_output=True)

    def test_fixtures_are_explicitly_fictional(self):
        latest = json.loads((ROOT / "data" / "latest.json").read_text())
        history = json.loads((ROOT / "data" / "history.json").read_text())
        self.assertEqual(len(history), 8)
        for point in history + [latest]:
            self.assertIs(point["meta"]["synthetic"], True)
            self.assertEqual(point["meta"]["generator"], generate_demo.GENERATOR)
            self.assertLess(point["meta"]["updated_at"], "2001")
            self.assertEqual(point["status"]["quality"], "synthetic")

    def test_fixture_verification_never_repairs_unexpected_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = isolated_project(directory)
            command = [sys.executable, str(root / "scripts" / "generate_demo.py")]
            subprocess.run(command, check=True, capture_output=True)
            latest_path = root / "data" / "latest.json"
            payload = json.loads(latest_path.read_text())
            payload["meta"]["synthetic"] = False
            changed = json.dumps(payload).encode()
            latest_path.write_bytes(changed)
            result = subprocess.run(command + ["--check"], capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(latest_path.read_bytes(), changed)

    def test_generation_uses_no_network_or_child_process(self):
        with mock.patch("socket.socket.connect", side_effect=AssertionError("network forbidden")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("child process forbidden")):
            latest = generate_demo.generate(check=True)
        self.assertEqual(len(latest["scoring"]["indicators"]), 20)

    def test_all_original_indicator_inputs_are_covered(self):
        latest = generate_demo.synthetic_point()
        for name, config in scoring.SCORING_CONFIG.items():
            with self.subTest(indicator=name):
                self.assertIsNotNone(scoring._get_nested(latest, config["data_path"]))
        result = scoring.calculate_score(latest, latest["meta"]["updated_ts"])
        # The unchanged engine does not coerce dictionary-valued ETF history to a
        # float, so that indicator keeps its original no-trend confidence of 0.7.
        etf = next(i for i in result.indicators if i.name == "etf_net_flow_pct")
        self.assertEqual(etf.confidence, 0.7)
        self.assertEqual(etf.trend_score, 0.0)
        self.assertEqual(result.confidence, 0.98)
        self.assertEqual({i.name for i in result.indicators}, set(scoring.SCORING_CONFIG))
        self.assertEqual(scoring.format_for_frontend(result), json.loads((ROOT / "data" / "latest.json").read_text())["scoring"])

    def test_missing_inputs_have_zero_confidence(self):
        result = scoring.calculate_score({}, 0)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.weighted_score, 0.0)
        self.assertTrue(all(i.signal == scoring.Signal.NEUTRAL for i in result.indicators))

    def test_scoring_still_supports_missing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = isolated_project(directory)
            spec = importlib.util.spec_from_file_location("scoring_without_history", root / "scripts" / "scoring.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            try:
                spec.loader.exec_module(module)
                result = module.calculate_score(generate_demo.synthetic_point(), 0)
                self.assertEqual(len(result.indicators), 20)
                self.assertEqual(result.confidence, 0.7)
                self.assertTrue(all(i.trend_score == 0.0 for i in result.indicators))
            finally:
                sys.modules.pop(spec.name, None)

    def test_synthetic_divergence_inputs_reach_existing_rules(self):
        point = copy.deepcopy(generate_demo.synthetic_point())
        point["macro"]["etf"] = {"example": {"change_pct": -2.0}}
        point["macro"]["derivatives"] = {"avg_funding_rate_pct": -0.03, "oi_change_24h": -6.0}
        point["onchain"].update(mvrv=4.0, nupl=0.8)
        result = scoring.calculate_score(point, 0)
        self.assertEqual(len(result.divergence_alerts), 5)


if __name__ == "__main__":
    unittest.main()
