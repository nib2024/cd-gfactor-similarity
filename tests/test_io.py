"""Unit tests for workbook parsing (both export layouts)."""

from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

import numpy as np
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cd_compare as C  # noqa: E402

SAMPLES = ["16-0", "14-2", "12-4", "10-6", "8-8",
           "6-10", "4-12", "2-14", "0-16"]


def _write_paired(path, x, ys):
    wb = openpyxl.Workbook()
    ws = wb.active
    for j, name in enumerate(SAMPLES):
        ws.cell(row=1, column=2 * j + 1, value=f"Sample: {name}")
        ws.cell(row=2, column=2 * j + 1, value="wavelength (nm)")
        ws.cell(row=2, column=2 * j + 2, value="g-factor")
    for i in range(len(x)):
        for j in range(len(SAMPLES)):
            ws.cell(row=3 + i, column=2 * j + 1, value=float(x[i]))
            ws.cell(row=3 + i, column=2 * j + 2, value=float(ys[j][i]))
    # trailing metadata block must be ignored
    ws.cell(row=4 + len(x), column=1, value="Scanning speed")
    ws.cell(row=4 + len(x), column=2, value="200 nm/min")
    wb.save(path)


def _write_shared(path, x, ys):
    wb = openpyxl.Workbook()
    ws = wb.active
    for j, name in enumerate(SAMPLES):
        ws.cell(row=1, column=2 + j, value=f"Sample: {name}")
    ws.cell(row=2, column=1, value="wavelength (nm)")
    for j in range(len(SAMPLES)):
        ws.cell(row=2, column=2 + j, value="g-factor")
    for i in range(len(x)):
        ws.cell(row=3 + i, column=1, value=float(x[i]))
        for j in range(len(SAMPLES)):
            ws.cell(row=3 + i, column=2 + j, value=float(ys[j][i]))
    wb.save(path)


class TestParsing(unittest.TestCase):
    def setUp(self):
        self.x = np.arange(600.0, 199.9, -1.0)
        self.ys = [np.sin(self.x / (20.0 + k)) * 1e-3 for k in range(len(SAMPLES))]

    def _check(self, samples):
        self.assertEqual(len(samples), 9)
        self.assertEqual([s["name"] for s in samples], SAMPLES)
        for s in samples:
            self.assertEqual(len(s["W"]), 401)
            self.assertTrue(np.all(np.diff(s["W"]) > 0))
            self.assertAlmostEqual(s["W"][0], 200.0, places=6)
            self.assertAlmostEqual(s["W"][-1], 600.0, places=6)

    def test_paired_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "paired.xlsx"
            _write_paired(path, self.x, self.ys)
            self._check(C.read_cd_workbook(path))

    def test_shared_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "shared.xlsx"
            _write_shared(path, self.x, self.ys)
            self._check(C.read_cd_workbook(path))

    def test_sample_name(self):
        self.assertEqual(C.parse_sample_name("16-0"), (16, 0, "pure_thiol2"))
        self.assertEqual(C.parse_sample_name("0-16"), (0, 16, "pure_thiol1"))
        self.assertEqual(C.parse_sample_name("8-8"), (8, 8, "mixture"))


if __name__ == "__main__":
    unittest.main()
