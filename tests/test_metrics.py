"""Unit tests for the numerical core (no external test framework)."""

from __future__ import annotations

import pathlib
import sys
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cd_metrics as M  # noqa: E402


def gauss(x, center, sigma, amp):
    return amp * np.exp(-0.5 * ((x - center) / sigma) ** 2)


def base_spectrum(x):
    return (gauss(x, 340.0, 12.0, 2.0) - gauss(x, 385.0, 14.0, 1.5)
            + 8.0e-4 * (x - 280.0) / 240.0)


class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.x = M.GRID
        self.p0 = M.prepare(self.x, base_spectrum(self.x))

    def test_self_correlation(self):
        for key in ("raw", "hp", "deriv"):
            s = M.summarize_profile(M.corr_profile(self.p0[key], self.p0[key]))
            self.assertAlmostEqual(s["S"], 1.0, places=6)
            self.assertEqual(s["dS"], 0.0)

    def test_mirror(self):
        pm = M.prepare(self.x, -base_spectrum(self.x))
        s = M.summarize_profile(M.corr_profile(self.p0["deriv"], pm["deriv"]))
        self.assertGreaterEqual(s["M"], 0.95)
        self.assertLessEqual(abs(s["dM"]), 0.5)

    def test_shift_recovery(self):
        for shift in (-12.0, -5.0, 5.0, 12.0, 20.0):
            y = (gauss(self.x, 340.0 + shift, 12.0, 2.0)
                 - gauss(self.x, 385.0 + shift, 14.0, 1.5)
                 + 8.0e-4 * (self.x - 280.0) / 240.0)
            p1 = M.prepare(self.x, y)
            s = M.summarize_profile(M.corr_profile(self.p0["deriv"], p1["deriv"]))
            self.assertLessEqual(abs(s["dS"] - shift), 0.5)

    def test_bh_fdr_monotone(self):
        p = np.array([0.001, 0.01, 0.02, 0.5, 0.9])
        q = M.bh_fdr(p)
        self.assertTrue(np.all(q >= p - 1e-12))
        self.assertTrue(np.all(np.diff(q[np.argsort(p)]) >= -1e-12))

    def test_classify_thresholds(self):
        t = M.DEFAULT_THRESHOLDS
        self.assertEqual(M.classify(0.95, 0.1, 0.0, -20.0, 0.001, 0.5, 100, 1.0, 3, t),
                         "同手性·高度一致")
        self.assertEqual(M.classify(0.95, 0.1, 8.0, -20.0, 0.001, 0.5, 100, 1.0, 3, t),
                         "同手性·位移型")
        self.assertEqual(M.classify(0.2, 0.95, -20.0, 0.0, 0.5, 0.001, 100, 1.0, 3, t),
                         "镜像·手性翻转")
        self.assertEqual(M.classify(0.2, 0.1, 0.0, 0.0, 0.5, 0.5, 5, 1.0, 3, t),
                         "弱/不可判定")


if __name__ == "__main__":
    unittest.main()
