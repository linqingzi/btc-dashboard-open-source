"""Verify the public static bundle boundary, including rejected input and output."""

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_static_demo


def project_copy(directory):
    project = pathlib.Path(directory) / "source"
    for name in (
        "index.html", "app.js", "i18n.js", "LICENSE", "data/latest.json", "data/history.json",
        "scripts/scoring.py", "scripts/generate_demo.py", "scripts/build_static_demo.py",
    ):
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return project


class StaticDemoTests(unittest.TestCase):
    def test_bundle_only_contains_public_runtime_and_license(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "demo"
            build_static_demo.build(output)
            expected = {"index.html", "app.js", "i18n.js", "data/latest.json", "LICENSE", ".nojekyll"}
            self.assertEqual({p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}, expected)
            for name in expected - {".nojekyll"}:
                self.assertEqual((output / name).read_bytes(), (ROOT / name).read_bytes())
            # Rebuilding the same dedicated bundle remains reproducible.
            build_static_demo.build(output)
            self.assertEqual((output / ".nojekyll").read_bytes(), b"")

    def test_changed_data_cannot_be_published_under_a_synthetic_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            project = project_copy(directory)
            latest = project / "data/latest.json"
            latest.write_text(latest.read_text().replace('"usd": 10000.0', '"usd": 9999.0'))
            self.assertNotEqual(latest.read_bytes(), (ROOT / "data/latest.json").read_bytes())
            output = pathlib.Path(directory) / "output"
            result = subprocess.run([sys.executable, str(project / "scripts/build_static_demo.py"), "--output", str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_unexpected_output_is_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "demo"
            output.mkdir()
            sentinel = output / "account-record.txt"
            sentinel.write_text("invented test sentinel")
            with self.assertRaises(ValueError):
                build_static_demo.build(output)
            self.assertEqual(sentinel.read_text(), "invented test sentinel")
            self.assertFalse((output / "index.html").exists())

    def test_source_symlink_cannot_include_an_unrelated_file(self):
        with tempfile.TemporaryDirectory() as directory:
            project = project_copy(directory)
            unrelated = pathlib.Path(directory) / "unrelated-test-file.txt"
            unrelated.write_text("invented test sentinel")
            (project / "app.js").unlink()
            (project / "app.js").symlink_to(unrelated)
            output = pathlib.Path(directory) / "output"
            result = subprocess.run([sys.executable, str(project / "scripts/build_static_demo.py"), "--output", str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
