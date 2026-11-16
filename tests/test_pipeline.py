"""End-to-end smoke test on the synthetic demo dataset."""

from __future__ import annotations

import csv
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestPipeline(unittest.TestCase):
    def test_demo_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp) / "demo_data"
            out = pathlib.Path(tmp) / "out"
            subprocess.run(
                [sys.executable, str(ROOT / "examples" / "make_demo_data.py"),
                 "--out", str(data)],
                check=True, capture_output=True,
            )
            subprocess.run(
                [sys.executable, str(ROOT / "cd_compare.py"),
                 "--input", str(data), "--out", str(out),
                 "--surrogates", "50"],
                check=True, capture_output=True,
            )
            with open(out / "pairwise_metrics.csv", encoding="utf-8-sig") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 72)  # 2 workbooks x 36 pairs
            self.assertTrue((out / "CD_similarity_results.xlsx").exists())
            self.assertTrue(any(r["decision"].startswith("镜像") for r in rows))


if __name__ == "__main__":
    unittest.main()
