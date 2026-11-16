#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a small synthetic demo dataset for the CD g-factor pipeline.

The demo reproduces the two workbook layouts found in the experimental
exports:

* paired columns   : wavelength | g-factor | wavelength | g-factor | ...
* shared wavelength: wavelength | g-factor | g-factor | ...

Two workbooks with nine samples each are written.  Workbook A contains a
clear mirror-image block (samples 16-0 ... 10-6 versus 8-8 ... 2-14);
workbook B contains only same-sense spectra with small rigid shifts.

Usage
-----
python examples/make_demo_data.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import openpyxl

SAMPLES = ["16-0", "14-2", "12-4", "10-6", "8-8",
           "6-10", "4-12", "2-14", "0-16"]


def spectrum(x, sign=1.0, shift=0.0, noise=0.0, rng=None):
    """Two Gaussian Cotton bands on a weak sloping background."""
    y = (3.0e-3 * np.exp(-0.5 * ((x - 345.0 - shift) / 18.0) ** 2)
         - 2.0e-3 * np.exp(-0.5 * ((x - 385.0 - shift) / 20.0) ** 2))
    y = sign * y + 5.0e-4 * (x - 200.0) / 400.0
    if noise and rng is not None:
        y = y + rng.normal(0.0, noise, size=y.shape)
    return y


def write_paired(path, x, columns):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for j, (name, _) in enumerate(columns):
        ws.cell(row=1, column=2 * j + 1, value=f"Sample: {name}")
        ws.cell(row=2, column=2 * j + 1, value="wavelength (nm)")
        ws.cell(row=2, column=2 * j + 2, value="g-factor")
    for i in range(len(x)):
        for j, (_, y) in enumerate(columns):
            ws.cell(row=3 + i, column=2 * j + 1, value=float(x[i]))
            ws.cell(row=3 + i, column=2 * j + 2, value=float(y[i]))
    wb.save(path)


def write_shared(path, x, columns):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.cell(row=1, column=1, value=None)
    for j, (name, _) in enumerate(columns):
        ws.cell(row=1, column=2 + j, value=f"Sample: {name}")
    ws.cell(row=2, column=1, value="wavelength (nm)")
    for j in range(len(columns)):
        ws.cell(row=2, column=2 + j, value="g-factor")
    for i in range(len(x)):
        ws.cell(row=3 + i, column=1, value=float(x[i]))
        for j, (_, y) in enumerate(columns):
            ws.cell(row=3 + i, column=2 + j, value=float(y[i]))
    wb.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="examples/demo_data")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    x = np.arange(600.0, 199.9, -1.0)          # descending, as exported

    # Workbook A: mirror block between the two composition halves.
    cols_a = []
    for k, name in enumerate(SAMPLES):
        sign = 1.0 if k <= 3 else (-1.0 if k <= 7 else 0.15)
        cols_a.append((name, spectrum(x, sign=sign, noise=2.0e-5, rng=rng)))
    write_paired(out / "demo_01_1_MPAOMe_Lcys.xlsx", x, cols_a)

    # Workbook B: same sense, progressively shifted, no mirror block.
    cols_b = []
    for k, name in enumerate(SAMPLES):
        cols_b.append((name, spectrum(x, sign=1.0, shift=2.0 * k,
                                     noise=2.0e-5, rng=rng)))
    write_shared(out / "demo_01_2_MPA_Lcys.xlsx", x, cols_b)

    print(f"Wrote demo workbooks to {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
