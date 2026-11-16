#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CD (g-factor) spectral similarity / mirror-similarity pipeline.

Reads every workbook in ``01_raw data``, compares the nine spectra inside
each workbook (only within a workbook), searches a global wavelength shift
of +/-20 nm, tests same-sense vs mirror similarity, and writes an Excel
workbook + CSV tables + a Chinese Markdown report.

Usage
-----
python cd_compare.py --input "../01_raw data" --out "out"
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import openpyxl
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import cd_metrics as M

# ----------------------------------------------------------------------
# configuration
# ----------------------------------------------------------------------
SAMPLE_ORDER = ["16-0", "14-2", "12-4", "10-6", "8-8",
                "6-10", "4-12", "2-14", "0-16"]

CATEGORIES = [
    "同手性·高度一致",
    "同手性·位移型",
    "镜像·手性翻转",
    "镜像+位移",
    "弱/不可判定",
    "不相似",
]

N_SUR = 2000          # phase-randomised surrogates per pair
SEED = 20261114

DEFAULT_T = dict(M.DEFAULT_THRESHOLDS)

# ----------------------------------------------------------------------
# styles
# ----------------------------------------------------------------------
HDR_FILL = PatternFill("solid", fgColor="1F4E78")
HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
TITLE_FONT = Font(bold=True, size=13, color="1F4E78")
SUB_FONT = Font(bold=True, size=11, color="1F4E78")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

DEC_FILL = {
    "同手性·高度一致": "C6EFCE",
    "同手性·位移型": "FFEB9C",
    "镜像·手性翻转": "FFC7CE",
    "镜像+位移": "F8CBAD",
    "弱/不可判定": "D9D9D9",
    "不相似": "E7E6E6",
}
CONF_FILL = {"高": "C6EFCE", "中": "FFEB9C", "低": "D9D9D9"}

# qualitative palette for up to 9 spectra
PALETTE = ["1F77B4", "FF7F0E", "2CA02C", "D62728", "9467BD",
           "8C564B", "E377C2", "7F7F7F", "BCBD22"]


def nice_ceil(x: float) -> float:
    """Round a positive magnitude up to a 'nice' 1/1.5/2/2.5/3/4/5/6/8 x 10^k."""
    if not np.isfinite(x) or x <= 0:
        return 1.0
    exp = math.floor(math.log10(x))
    base = 10.0 ** exp
    for f in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0):
        if x <= f * base:
            return f * base
    return 10.0 * base


def _v(x):
    """Convert numpy scalars to python scalars for openpyxl."""
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def _f(x, nd=4):
    try:
        if x is None or not np.isfinite(float(x)):
            return "—"
        return round(float(x), nd)
    except (TypeError, ValueError):
        return x


# ----------------------------------------------------------------------
# workbook parsing
# ----------------------------------------------------------------------
def _is_num(v) -> bool:
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(float(v)))


def _is_wl(v) -> bool:
    return isinstance(v, str) and v.strip().lower().startswith("wavelength")


def parse_sample_name(name: str):
    """'16-0' -> (16, 0, 'pure_thiol2')."""
    parts = name.split("-")
    if len(parts) != 2:
        return (None, None, "unknown")
    try:
        n3, n4 = int(parts[0]), int(parts[1])
    except ValueError:
        return (None, None, "unknown")
    if n4 == 0:
        return (n3, n4, "pure_thiol2")
    if n3 == 0:
        return (n3, n4, "pure_thiol1")
    return (n3, n4, "mixture")


def read_cd_workbook(path: Path):
    """Return a list of samples in header order.

    Handles both layouts found in the raw data:
      * shared wavelength column: A=wavelength, B..J = g-factor
      * interleaved pairs:        wavelength, g-factor, wavelength, ...
    Metadata / text cells are skipped by requiring both cells numeric.
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()

    if len(rows) < 3:
        raise ValueError(f"{path.name}: too few rows")

    header, sub = rows[0], rows[1]
    wl_cols = [i for i, v in enumerate(sub) if _is_wl(v)]
    paired = len(wl_cols) > 1

    if paired:
        blocks = [(i, i + 1, i) for i in wl_cols
                  if i < len(header) and header[i] is not None]
    else:
        blocks = [(0, i, i) for i in range(1, len(header))
                  if header[i] is not None]

    samples = []
    for wc, gc, name_col in blocks:
        raw_name = header[name_col]
        name = str(raw_name).replace("Sample:", "").strip()
        W, G = [], []
        for r in rows[2:]:
            w = r[wc] if wc < len(r) else None
            g = r[gc] if gc < len(r) else None
            if _is_num(w) and _is_num(g):
                W.append(float(w))
                G.append(float(g))
        if len(W) < 50:
            continue
        W = np.asarray(W, float)
        G = np.asarray(G, float)
        order = np.argsort(W)
        W, G = W[order], G[order]
        uw, inv = np.unique(W, return_inverse=True)
        if len(uw) < len(W):
            G = np.array([G[inv == k].mean() for k in range(len(uw))])
            W = uw
        samples.append({"name": name, "W": W, "G": G})
    return samples


# ----------------------------------------------------------------------
# QC
# ----------------------------------------------------------------------
def spike_count(y: np.ndarray, k: int = 7) -> int:
    y = np.asarray(y, float)
    half = k // 2
    if len(y) < k + 2:
        return 0
    win = np.lib.stride_tricks.sliding_window_view(y, k)
    med = np.median(win, axis=1)
    dev = np.abs(y[half:len(y) - half] - med)
    rng = np.percentile(y, 98) - np.percentile(y, 2)
    if rng <= 0:
        return 0
    return int(np.sum(dev > 0.4 * rng))


def build_record(file_stem: str, sample: dict) -> dict:
    W, G = sample["W"], sample["G"]
    interp = np.interp(M.GRID, W, G)
    qc = M.qc_stats(interp)
    prep = M.prepare(W, G)
    bands = M.find_bands(prep["interp"])
    dom = max(bands, key=lambda b: abs(b["amp"])) if bands else None
    win = (M.GRID >= 300) & (M.GRID <= 500)
    n3, n4, endpoint = parse_sample_name(sample["name"])
    return {
        "file": file_stem,
        "name": sample["name"],
        "n3": n3,
        "n4": n4,
        "endpoint": endpoint,
        "n": int(len(W)),
        "wmin": float(W.min()),
        "wmax": float(W.max()),
        "step": float(np.median(np.diff(W))) if len(W) > 1 else float("nan"),
        "n300": int(np.sum((W >= 300) & (W <= 500))),
        "covers_280_520": bool(W.min() <= 280.5 and W.max() >= 519.5),
        "amp": qc["amp"],
        "noise": qc["noise"],
        "snr": qc["snr"],
        "spikes": spike_count(interp[win]),
        "prep": prep,
        "bands": bands,
        "dom_lam": float(dom["lam"]) if dom else float("nan"),
        "dom_sign": float(dom["sign"]) if dom else float("nan"),
        "dom_amp": float(dom["amp"]) if dom else float("nan"),
    }


# ----------------------------------------------------------------------
# confidence / notes
# ----------------------------------------------------------------------
CONF_ORDER = {"高": 0, "中": 1, "低": 2}


def downgrade(conf: str, level: str) -> str:
    return conf if CONF_ORDER[conf] >= CONF_ORDER[level] else level


def pair_confidence(cat_raw, cat_hp, cat_d, qS, qM, snr_min, n_matched):
    c = {M.coarse(cat_raw), M.coarse(cat_hp), M.coarse(cat_d)}
    if len(c) == 1:
        conf = "高"
    elif cat_d == cat_hp or cat_d == cat_raw:
        conf = "中"
    else:
        conf = "低"
    if qS > DEFAULT_T["q"] and qM > DEFAULT_T["q"]:
        conf = downgrade(conf, "低")
    if snr_min < DEFAULT_T["snr"]:
        conf = downgrade(conf, "低")
    if n_matched < 2:
        conf = downgrade(conf, "中")
    return conf


def pair_notes(rec_a, rec_b, decision, dS, dM, band_dl, cat_raw, cat_d,
               n_matched, snr_min, qS, qM, S, Mv):
    notes = []
    if rec_a["endpoint"] != "mixture" or rec_b["endpoint"] != "mixture":
        notes.append(f"端元({rec_a['endpoint']}/{rec_b['endpoint']})")
    # only the shift that matters for the decision is checked
    d_used = dM if decision.startswith("镜像") else dS
    if abs(d_used) >= 19.5:
        notes.append("位移触边(≥20nm)")
    if snr_min < DEFAULT_T["snr"]:
        notes.append("低SNR")
    if n_matched < 2:
        notes.append("带级证据不足")
    if n_matched >= 2 and np.isfinite(band_dl) and abs(d_used - band_dl) > 5.0:
        notes.append("位移估计不一致")
    if M.coarse(cat_raw) != M.coarse(cat_d):
        notes.append("raw受背景影响")
    if decision == "弱/不可判定" and max(S, Mv) >= DEFAULT_T["s"] and qS > DEFAULT_T["q"] and qM > DEFAULT_T["q"]:
        notes.append("统计不显著(q>0.05)")
    return "; ".join(notes)


# ----------------------------------------------------------------------
# pair computation
# ----------------------------------------------------------------------
def compute_pairs(records, rng, n_sur=N_SUR):
    pairs = []
    for a, b in itertools.combinations(records, 2):
        row = {
            "file": a["file"],
            "sample_A": a["name"],
            "sample_B": b["name"],
            "endpoint_A": a["endpoint"],
            "endpoint_B": b["endpoint"],
            "type": "endpoint" if "pure" in (a["endpoint"], b["endpoint"]) else "mixture",
        }

        profiles = {}
        for key in ("raw", "hp", "deriv"):
            r = M.corr_profile(a["prep"][key], b["prep"][key])
            profiles[key] = r
            sm = M.summarize_profile(r)
            row[f"S_{key}"] = sm["S"]
            row[f"dS_{key}"] = sm["dS"]
            row[f"M_{key}"] = sm["M"]
            row[f"dM_{key}"] = sm["dM"]
            if key == "deriv":
                row["r0_d"] = sm["r0"]

        # complementary metrics on raw profile
        cos = M.cosine_profile(a["prep"]["raw"], b["prep"]["raw"])
        nr = M.nrmse_profile(a["prep"]["raw"], b["prep"]["raw"])
        row["cos_max"] = float(np.nanmax(cos))
        row["SAM_deg"] = float(np.degrees(np.arccos(np.clip(np.nanmax(cos), -1, 1))))
        row["NRMSE_min"] = float(np.nanmin(nr))

        # mirror margin
        row["margin_d"] = row["M_deriv"] - row["S_deriv"]
        denom = row["M_deriv"] + row["S_deriv"]
        row["mirror_index_d"] = row["margin_d"] / denom if abs(denom) > 1e-12 else float("nan")

        # surrogate null (derivative only)
        s_null, m_null = M.surrogate_maxima(
            a["prep"]["deriv"], b["prep"]["deriv"], n_sur, rng
        )
        row["pS"] = float((1 + np.sum(s_null >= row["S_deriv"])) / (1 + n_sur))
        row["pM"] = float((1 + np.sum(m_null >= row["M_deriv"])) / (1 + n_sur))

        # bands
        mb = M.match_bands(a["bands"], b["bands"])
        row["band_n"] = mb["n"]
        row["band_same"] = mb["same"]
        row["band_mirror"] = mb["mirror"]
        row["band_median_dl"] = mb["median_dl"]

        row["snr_A"] = a["snr"]
        row["snr_B"] = b["snr"]
        row["_profiles"] = profiles
        row["_a"] = a
        row["_b"] = b
        pairs.append(row)
    return pairs


def finalize_pairs(pairs, thresholds=None):
    t = dict(DEFAULT_T)
    if thresholds:
        t.update(thresholds)

    # BH-FDR is applied within each workbook (36 tests per family), not
    # across all 288 pairs:  with 2000 surrogates the smallest attainable
    # p is 5e-4, so a 288-test family could never reach q<0.05.
    qS = np.full(len(pairs), np.nan)
    qM = np.full(len(pairs), np.nan)
    for stem in sorted({r["file"] for r in pairs}):
        idx = [i for i, r in enumerate(pairs) if r["file"] == stem]
        qS[idx] = M.bh_fdr([pairs[i]["pS"] for i in idx])
        qM[idx] = M.bh_fdr([pairs[i]["pM"] for i in idx])

    for r, qs, qm in zip(pairs, qS, qM):
        r["qS"] = float(qs)
        r["qM"] = float(qm)
        snr_min = min(r["snr_A"], r["snr_B"])
        band_mirror = r["band_mirror"] if np.isfinite(r["band_mirror"]) else float("nan")

        cats = {}
        for key in ("raw", "hp", "deriv"):
            cats[key] = M.classify(
                r[f"S_{key}"], r[f"M_{key}"], r[f"dS_{key}"], r[f"dM_{key}"],
                r["qS"] if key == "deriv" else 0.0,
                r["qM"] if key == "deriv" else 0.0,
                snr_min, band_mirror, r["band_n"], t,
            )
        r["cat_raw"] = cats["raw"]
        r["cat_hp"] = cats["hp"]
        r["decision"] = cats["deriv"]
        r["confidence"] = pair_confidence(
            cats["raw"], cats["hp"], cats["deriv"], r["qS"], r["qM"], snr_min, r["band_n"]
        )
        # a "weak / dissimilar" verdict is inherently low-confidence
        if r["decision"] in ("弱/不可判定", "不相似"):
            r["confidence"] = "低"
        r["notes"] = pair_notes(
            r["_a"], r["_b"], r["decision"], r["dS_deriv"], r["dM_deriv"],
            r["band_median_dl"], cats["raw"], cats["deriv"],
            r["band_n"], snr_min, r["qS"], r["qM"], r["S_deriv"], r["M_deriv"],
        )
    return pairs


# ----------------------------------------------------------------------
# Excel helpers
# ----------------------------------------------------------------------
def style_header(ws, row, ncol):
    for j in range(1, ncol + 1):
        c = ws.cell(row=row, column=j)
        c.fill = HDR_FILL
        c.font = HDR_FONT
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER


def write_row(ws, row, values, fmt=None, border=True):
    for j, v in enumerate(values, 1):
        c = ws.cell(row=row, column=j, value=_v(v))
        if border:
            c.border = BORDER
        if fmt and j in fmt and isinstance(v, (int, float, np.number)):
            c.number_format = fmt[j]


def set_widths(ws, widths):
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = w


# ----------------------------------------------------------------------
# Excel report
# ----------------------------------------------------------------------
def build_excel(path, records, pairs, file_stems, qc_ok, self_test_lines):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # ---------------- 00_说明 ----------------
    ws = wb.create_sheet("00_说明")
    ws["A1"] = "CD (g-factor) 谱图相似性 / 镜像相似性分析"
    ws["A1"].font = Font(bold=True, size=16, color="1F4E78")
    lines = [
        ("数据", "01_raw data/*.xlsx，8 个文件 × 9 条谱图 = 72 条；仅做同一文件内 9 条谱图的两两比较（36 对/文件，288 对），不做跨文件比较。"),
        ("窗口", "300–500 nm；统一网格 280–520 nm / 0.5 nm，位移时用 280–520 的填充数据，不截断比较窗口。"),
        ("位移", "每个谱对一个全局刚体位移 δ∈[−20,+20] nm，步长 0.5 nm；δ>0 表示 B 相对 A 红移。"),
        ("预处理", "升序排序 → 线性插值 → SG 平滑(11点/2阶) → raw / high-pass(减 61 点 SG) / 一阶导数(21点)。"),
        ("相似指标", "Pearson r、余弦相似度/SAM、NRMSE；S=max r，M=max(−r)。"),
        ("镜像", "A 与 −B 比较；M = −min r；镜像指数 = (M−S)/(M+S)。"),
        ("显著性", f"相位随机化 surrogate（{N_SUR} 次，保留功率谱、破坏对齐）；文件内 BH-FDR。"),
        ("判定阈值", "S/M ≥ 0.70；margin ≥ 0.20；位移 ≥ 3 nm；SNR ≥ 20；q < 0.05；镜像另需带级 mirror 一致率 ≥ 0.60（带数≥2 时）。"),
        ("带级", "SG 平滑后找 prominence ≥ 3×局部噪声、宽度 ≥ 4 nm 的前 4 个极值；按 |Δλ|≤20 nm 最优配对，按幅度加权比较符号。"),
        ("判定类别", "同手性·高度一致 / 同手性·位移型 / 镜像·手性翻转 / 镜像+位移 / 弱/不可判定 / 不相似。"),
        ("置信度", "高=raw/hp/deriv 粗分类一致；中=derivative 与其中一个一致；低=指标冲突或统计不显著。"),
        ("端元", "16-0 = 纯 thiol2；0-16 = 纯 thiol1；两列跨文件存在完全相同的情况（纯样品复用），本表只做文件内比较并单独标记。"),
        ("限制", "g-factor = Δε/ε；只有 g 谱时，可区分镜像（符号翻转）与非镜像（形状/位移），但不能把非镜像变化唯一归因于 CD 带位移或吸收带位移。"),
        ("主带", "01_QC / 06_峰位表 的“主带”是平滑后 |g| 最大的极值；对弱谱或端元样品，它可能是 420–500 nm 的背景尾而不是 Cotton 带，需结合幅度/SNR 判断。"),
        ("文件", "01_QC / 02_配对总表 / 03_相似度矩阵 / 04_镜像矩阵 / 05_位移矩阵 / 06_峰位表 / 07_最佳配对 / 08_图表 / 09_结论摘要 / 10_谱图数据 / 13_镜像分组 / 14_最佳谱对。"),
    ]
    for i, (k, v) in enumerate(lines, start=3):
        ws.cell(row=i, column=1, value=k).font = Font(bold=True)
        ws.cell(row=i, column=2, value=v).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 120

    # self test block
    r0 = 3 + len(lines) + 1
    ws.cell(row=r0, column=1, value="自检").font = Font(bold=True, color="C00000")
    for i, line in enumerate(self_test_lines, start=1):
        ws.cell(row=r0 + i, column=1, value=line)

    # ---------------- 01_QC ----------------
    ws = wb.create_sheet("01_QC")
    headers = ["文件", "样品", "类型", "点数", "λmin", "λmax", "步长",
               "300-500点数", "覆盖280-520", "幅度", "噪声", "SNR",
               "主带λ", "主带符号", "主带g", "带数", "尖峰点数"]
    ws.append(headers)
    style_header(ws, 1, len(headers))
    for rec in records:
        write_row(ws, ws.max_row + 1, [
            rec["file"], rec["name"], rec["endpoint"], rec["n"],
            rec["wmin"], rec["wmax"], rec["step"], rec["n300"],
            "是" if rec["covers_280_520"] else "否",
            rec["amp"], rec["noise"], rec["snr"],
            rec["dom_lam"], rec["dom_sign"], rec["dom_amp"],
            len(rec["bands"]), rec["spikes"],
        ], fmt={5: "0.0", 6: "0.0", 7: "0.00", 10: "0.000E+00",
                11: "0.000E+00", 12: "0.0", 13: "0.0", 15: "0.000E+00"})
    set_widths(ws, [26, 9, 12, 7, 7, 7, 7, 10, 11, 11, 11, 9, 8, 8, 11, 6, 9])
    ws.freeze_panes = "A2"

    # ---------------- 02_配对总表 ----------------
    ws = wb.create_sheet("02_配对总表")
    headers = [
        "文件", "样品A", "样品B", "A类型", "B类型", "对类型",
        "S_raw", "δS_raw", "M_raw", "δM_raw",
        "S_hp", "δS_hp", "M_hp", "δM_hp",
        "S_d", "δS_d", "M_d", "δM_d", "r0_d",
        "margin_d", "mirror_index", "pS", "pM", "qS", "qM",
        "带数", "同号一致", "镜像一致", "带中位Δλ",
        "SNR_A", "SNR_B", "判定", "置信度", "备注",
    ]
    ws.append(headers)
    style_header(ws, 1, len(headers))
    for r in pairs:
        write_row(ws, ws.max_row + 1, [
            r["file"], r["sample_A"], r["sample_B"], r["endpoint_A"], r["endpoint_B"], r["type"],
            r["S_raw"], r["dS_raw"], r["M_raw"], r["dM_raw"],
            r["S_hp"], r["dS_hp"], r["M_hp"], r["dM_hp"],
            r["S_deriv"], r["dS_deriv"], r["M_deriv"], r["dM_deriv"], r["r0_d"],
            r["margin_d"], r["mirror_index_d"], r["pS"], r["pM"], r["qS"], r["qM"],
            r["band_n"], r["band_same"], r["band_mirror"], r["band_median_dl"],
            r["snr_A"], r["snr_B"], r["decision"], r["confidence"], r["notes"],
        ], fmt={7: "0.000", 8: "0.0", 9: "0.000", 10: "0.0",
                11: "0.000", 12: "0.0", 13: "0.000", 14: "0.0",
                15: "0.000", 16: "0.0", 17: "0.000", 18: "0.0", 19: "0.000",
                20: "0.000", 21: "0.000", 22: "0.0000", 23: "0.0000",
                24: "0.0000", 25: "0.0000", 26: "0.0", 27: "0.00",
                28: "0.00", 29: "0.0", 30: "0", 31: "0"})
        rr = ws.max_row
        dec = ws.cell(row=rr, column=32)
        dec.fill = PatternFill("solid", fgColor=DEC_FILL.get(r["decision"], "FFFFFF"))
        conf = ws.cell(row=rr, column=33)
        conf.fill = PatternFill("solid", fgColor=CONF_FILL.get(r["confidence"], "FFFFFF"))
    set_widths(ws, [26, 8, 8, 12, 12, 9] + [8] * 23 + [18, 8, 50])
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"

    # ---------------- matrices ----------------
    def matrix_sheet(title, key, fmt, cscale, diagonal_nan=False):
        wsx = wb.create_sheet(title)
        row = 1
        for stem in file_stems:
            wsx.cell(row=row, column=1, value=stem).font = TITLE_FONT
            row += 1
            names = [r["name"] for r in records if r["file"] == stem]
            wsx.cell(row=row, column=1, value="")
            for j, nm in enumerate(names, 2):
                c = wsx.cell(row=row, column=j, value=nm)
                c.fill = HDR_FILL
                c.font = HDR_FONT
                c.alignment = Alignment(horizontal="center")
            row += 1
            mat = np.full((len(names), len(names)), np.nan)
            for pr in pairs:
                if pr["file"] != stem:
                    continue
                i = names.index(pr["sample_A"])
                j = names.index(pr["sample_B"])
                val = pr[key]
                mat[i, j] = val
                # S and M are symmetric; the shift is directional (B relative to A)
                mat[j, i] = -val if key.startswith("dS") else val
            for i, nm in enumerate(names):
                c = wsx.cell(row=row, column=1, value=nm)
                c.fill = HDR_FILL
                c.font = HDR_FONT
                c.alignment = Alignment(horizontal="center")
                for j in range(len(names)):
                    v = mat[i, j]
                    if i == j:
                        v = 1.0 if key.startswith("S") else (np.nan if diagonal_nan else 0.0)
                    cc = wsx.cell(row=row, column=2 + j, value=None if not np.isfinite(v) else round(float(v), 3))
                    cc.border = BORDER
                    cc.alignment = Alignment(horizontal="center")
                    if fmt:
                        cc.number_format = fmt
                row += 1
            # conditional formatting across the 9x9 block
            rng = f"B{row - len(names)}:J{row - 1}"
            wsx.conditional_formatting.add(rng, cscale)
            row += 2
        wsx.column_dimensions["A"].width = 9
        for j in range(2, 11):
            wsx.column_dimensions[get_column_letter(j)].width = 7

    red_white_blue = ColorScaleRule(
        start_type="num", start_value=-1, start_color="F8696B",
        mid_type="num", mid_value=0, mid_color="FFFFFF",
        end_type="num", end_value=1, end_color="5A8AC6",
    )
    blue_white_red = ColorScaleRule(
        start_type="num", start_value=-20, start_color="5A8AC6",
        mid_type="num", mid_value=0, mid_color="FFFFFF",
        end_type="num", end_value=20, end_color="F8696B",
    )
    matrix_sheet("03_相似度矩阵", "S_deriv", "0.000", red_white_blue, diagonal_nan=False)
    matrix_sheet("04_镜像矩阵", "M_deriv", "0.000", red_white_blue, diagonal_nan=True)
    matrix_sheet("05_位移矩阵", "dS_deriv", "0.0", blue_white_red, diagonal_nan=False)

    # ---------------- 06_峰位表 ----------------
    ws = wb.create_sheet("06_峰位表")
    headers = ["文件", "样品", "类型", "主带λ", "主带符号"]
    for k in range(1, 5):
        headers += [f"带{k}λ", f"带{k}符号", f"带{k}g", f"带{k}prom"]
    ws.append(headers)
    style_header(ws, 1, len(headers))
    for rec in records:
        vals = [rec["file"], rec["name"], rec["endpoint"], rec["dom_lam"], rec["dom_sign"]]
        for k in range(4):
            if k < len(rec["bands"]):
                b = rec["bands"][k]
                vals += [b["lam"], b["sign"], b["amp"], b["prom"]]
            else:
                vals += ["—", "—", "—", "—"]
        write_row(ws, ws.max_row + 1, vals, fmt={4: "0.0", 5: "0",
                                                 7: "0.0", 8: "0", 9: "0.000E+00", 10: "0.000E+00"})
    set_widths(ws, [26, 8, 12, 8, 7] + [8, 7, 11, 11] * 4)

    # ---------------- 07_最佳配对 ----------------
    ws = wb.create_sheet("07_最佳配对")
    headers = ["文件", "样品", "最相似1", "S1", "最相似2", "S2", "最相似3", "S3",
               "最镜像1", "M1", "最镜像2", "M2", "最镜像3", "M3"]
    ws.append(headers)
    style_header(ws, 1, len(headers))
    by_file = {}
    for pr in pairs:
        by_file.setdefault(pr["file"], []).append(pr)
    for rec in records:
        stem, name = rec["file"], rec["name"]
        same, mir = [], []
        for pr in by_file.get(stem, []):
            if pr["sample_A"] == name:
                other, S, Mv = pr["sample_B"], pr["S_deriv"], pr["M_deriv"]
            elif pr["sample_B"] == name:
                other, S, Mv = pr["sample_A"], pr["S_deriv"], pr["M_deriv"]
            else:
                continue
            same.append((other, S))
            mir.append((other, Mv))
        same.sort(key=lambda t: -t[1])
        mir.sort(key=lambda t: -t[1])
        vals = [stem, name]
        for k in range(3):
            vals += [same[k][0], same[k][1]] if k < len(same) else ["—", "—"]
        for k in range(3):
            vals += [mir[k][0], mir[k][1]] if k < len(mir) else ["—", "—"]
        write_row(ws, ws.max_row + 1, vals,
                  fmt={4: "0.000", 6: "0.000", 8: "0.000", 10: "0.000", 12: "0.000", 14: "0.000"})
    set_widths(ws, [26, 8] + [8, 8] * 6)

    # ---------------- 09_结论摘要 ----------------
    ws = wb.create_sheet("09_结论摘要")
    ws["A1"] = "每个文件的判定计数"
    ws["A1"].font = TITLE_FONT
    headers = ["文件", "对数"] + CATEGORIES + ["同手性合计", "镜像合计", "弱/不相似"]
    for j, h in enumerate(headers, 1):
        ws.cell(row=3, column=j, value=h)
    style_header(ws, 3, len(headers))
    for stem in file_stems:
        ps = [p for p in pairs if p["file"] == stem]
        cnt = Counter(p["decision"] for p in ps)
        same_n = sum(cnt[c] for c in CATEGORIES if c.startswith("同手性"))
        mir_n = sum(cnt[c] for c in CATEGORIES if c.startswith("镜像"))
        weak_n = cnt["弱/不可判定"] + cnt["不相似"]
        write_row(ws, ws.max_row + 1, [stem, len(ps)] + [cnt[c] for c in CATEGORIES] + [same_n, mir_n, weak_n])
    set_widths(ws, [26, 7] + [20] * len(CATEGORIES) + [12, 12, 12])
    ws.row_dimensions[3].height = 32

    # threshold sensitivity
    r0 = ws.max_row + 2
    ws.cell(row=r0, column=1, value="阈值敏感性（改变阈值后判定类别发生变化的对数 / 288）").font = SUB_FONT
    sens_rows = threshold_sensitivity(pairs)
    ws.cell(row=r0 + 1, column=1, value="设置")
    ws.cell(row=r0 + 1, column=2, value="改变对数")
    style_header(ws, r0 + 1, 2)
    for i, (label, n) in enumerate(sens_rows, start=1):
        ws.cell(row=r0 + 1 + i, column=1, value=label)
        ws.cell(row=r0 + 1 + i, column=2, value=n)
    ws.column_dimensions["B"].width = 12

    # ---------------- 14_最佳谱对 ----------------
    ws = wb.create_sheet("14_最佳谱对")
    ws["A1"] = "最相似 / 最镜像的谱对（derivative 指标，全表）"
    ws["A1"].font = TITLE_FONT
    headers = ["类别", "文件", "A", "B", "S_d", "M_d", "判定", "置信度", "备注"]
    for j, h in enumerate(headers, 1):
        ws.cell(row=3, column=j, value=h)
    style_header(ws, 3, len(headers))
    top_same = sorted(pairs, key=lambda p: -p["S_deriv"])[:10]
    top_mir = sorted(pairs, key=lambda p: -p["M_deriv"])[:10]
    rr = 4
    for label, lst in (("S", top_same), ("M", top_mir)):
        for p in lst:
            write_row(ws, rr, [label, p["file"], p["sample_A"], p["sample_B"],
                               p["S_deriv"], p["M_deriv"], p["decision"],
                               p["confidence"], p["notes"]], fmt={5: "0.000", 6: "0.000"})
            rr += 1
    set_widths(ws, [7, 26, 8, 8, 9, 9, 20, 9, 50])
    ws.freeze_panes = "A4"

    # ---------------- 10_谱图数据 (charts source) ----------------
    ws_data = wb.create_sheet("10_谱图数据")
    block_rows = {}
    row = 1
    for stem in file_stems:
        chk = [r for r in records if r["file"] == stem]
        ws_data.cell(row=row, column=1, value=stem).font = Font(bold=True)
        row += 1
        ws_data.cell(row=row, column=1, value="wavelength (nm)")
        for j, rec in enumerate(chk, 2):
            ws_data.cell(row=row, column=j, value=rec["name"])
        row += 1
        start = row
        for k, lam in enumerate(np.arange(300.0, 500.0 + 1e-9, 1.0)):
            ws_data.cell(row=start + k, column=1, value=float(lam))
            for j, rec in enumerate(chk, 2):
                ws_data.cell(row=start + k, column=j, value=float(np.interp(lam, M.GRID, rec["prep"]["raw"])))
        block_rows[stem] = (start - 1, start, start + 200)  # header row, first data, last data
        row = start + 202
    set_widths(ws_data, [10] + [9] * 9)

    # ---------------- 08_图表 ----------------
    ws = wb.create_sheet("08_图表")
    anchors = []
    chart_pos = {"i": 0}

    def next_anchor():
        i = chart_pos["i"]
        chart_pos["i"] += 1
        r = 1 + (i // 2) * 21
        c = 1 + (i % 2) * 11
        return f"{get_column_letter(c)}{r}"

    for idx, stem in enumerate(file_stems):
        hdr, r_first, r_last = block_rows[stem]
        ch = ScatterChart()
        ch.title = stem
        ch.style = 13
        ch.x_axis.title = "Wavelength (nm)"
        ch.y_axis.title = "g-factor"
        ch.height = 9
        ch.width = 16
        ch.x_axis.delete = False
        ch.y_axis.delete = False
        ch.x_axis.scaling.min = 300
        ch.x_axis.scaling.max = 500
        ch.x_axis.majorUnit = 50
        ch.y_axis.number_format = "0.000E+00"
        ch.legend.position = "r"
        recs = [r for r in records if r["file"] == stem]
        ymax = max(float(np.max(np.abs(r["prep"]["raw"][M.WIN_START:M.WIN_START + M.NWIN])))
                   for r in recs)
        nice = nice_ceil(ymax)
        ch.y_axis.scaling.min = -nice
        ch.y_axis.scaling.max = nice
        ch.y_axis.majorUnit = nice / 4.0
        for j, rec in enumerate(recs, 2):
            xref = Reference(ws_data, min_col=1, min_row=r_first, max_row=r_last)
            yref = Reference(ws_data, min_col=j, min_row=r_first, max_row=r_last)
            s = Series(yref, xref, title=rec["name"])
            s.marker.symbol = "none"
            s.smooth = False
            color = PALETTE[(j - 2) % len(PALETTE)]
            s.graphicalProperties.line.solidFill = color
            s.graphicalProperties.line.width = 18000
            ch.series.append(s)
        anchor = next_anchor()
        ws.add_chart(ch, anchor)
        anchors.append(anchor)

    # S-M scatter
    ws_sm = wb.create_sheet("11_SM数据")
    ws_sm.append(["S_d", "M_d", "decision"])
    for p in pairs:
        ws_sm.append([p["S_deriv"], p["M_deriv"], p["decision"]])
    ch = ScatterChart()
    ch.title = "S (same) vs M (mirror)"
    ch.x_axis.title = "S = max r"
    ch.y_axis.title = "M = max(-r)"
    ch.height = 9
    ch.width = 12
    ch.style = 13
    ch.x_axis.scaling.min = -0.2
    ch.x_axis.scaling.max = 1.0
    ch.x_axis.majorUnit = 0.2
    ch.y_axis.scaling.min = -0.2
    ch.y_axis.scaling.max = 1.0
    ch.y_axis.majorUnit = 0.2
    ch.x_axis.number_format = "0.0"
    ch.y_axis.number_format = "0.0"
    xref = Reference(ws_sm, min_col=1, min_row=2, max_row=ws_sm.max_row)
    yref = Reference(ws_sm, min_col=2, min_row=2, max_row=ws_sm.max_row)
    s = Series(yref, xref, title="pairs")
    s.marker.symbol = "circle"
    s.marker.size = 6
    s.marker.graphicalProperties.solidFill = "1F77B4"
    s.marker.graphicalProperties.line.solidFill = "1F77B4"
    try:
        s.graphicalProperties.line.noFill = True
    except Exception:
        pass
    ch.series.append(s)
    ws.add_chart(ch, next_anchor())

    # representative pairs: prefer comparable amplitudes and non-boundary shifts
    def amp_ratio(p):
        lo = min(p["_a"]["amp"], p["_b"]["amp"])
        hi = max(p["_a"]["amp"], p["_b"]["amp"])
        return hi / lo if lo > 0 else 1e9

    reps = []
    mir = [p for p in pairs if p["decision"].startswith("镜像")]
    if mir:
        pool = [p for p in mir if amp_ratio(p) <= 5] or mir
        reps.append(("最佳镜像", max(pool, key=lambda p: p["M_deriv"])))
    same = [p for p in pairs if p["decision"] == "同手性·高度一致"]
    if same:
        pool = [p for p in same if amp_ratio(p) <= 5] or same
        reps.append(("最佳同手性", max(pool, key=lambda p: p["S_deriv"])))
    shifted = [p for p in pairs if p["decision"] == "同手性·位移型"]
    if shifted:
        pool = [p for p in shifted
                if amp_ratio(p) <= 5 and 8.0 <= abs(p["dS_deriv"]) < 19.5]
        if not pool:
            pool = ([p for p in shifted if amp_ratio(p) <= 5 and abs(p["dS_deriv"]) < 19.5]
                    or shifted)
        reps.append(("最佳位移", max(pool, key=lambda p: p["S_deriv"])))

    ws_rep = wb.create_sheet("12_代表谱对")
    row = 1
    for label, p in reps:
        a = p["_a"]; b = p["_b"]
        if label == "最佳镜像":
            metric = f"M={p['M_deriv']:.2f}, δM={p['dM_deriv']:+.1f} nm"
        else:
            metric = f"S={p['S_deriv']:.2f}, δS={p['dS_deriv']:+.1f} nm"
        ws_rep.cell(row=row, column=1,
                    value=f"{label}: {p['file']} / {p['sample_A']} vs {p['sample_B']}  ({metric}, 归一化)")
        ws_rep.cell(row=row, column=1).font = Font(bold=True)
        row += 1
        ws_rep.cell(row=row, column=1, value="wavelength")
        ws_rep.cell(row=row, column=2, value=p["sample_A"])
        ws_rep.cell(row=row, column=3, value=p["sample_B"])
        ws_rep.cell(row=row, column=4, value=f"-{p['sample_B']} (mirror)")
        row += 1
        first = row
        for lam in np.arange(300.0, 500.0 + 1e-9, 1.0):
            ya = float(np.interp(lam, M.GRID, a["prep"]["raw"]))
            yb = float(np.interp(lam, M.GRID, b["prep"]["raw"]))
            na = np.max(np.abs(a["prep"]["raw"][M.WIN_START:M.WIN_START + M.NWIN])) + 1e-15
            nb = np.max(np.abs(b["prep"]["raw"][M.WIN_START:M.WIN_START + M.NWIN])) + 1e-15
            ws_rep.cell(row=row, column=1, value=float(lam))
            ws_rep.cell(row=row, column=2, value=ya / na)
            ws_rep.cell(row=row, column=3, value=yb / nb)
            ws_rep.cell(row=row, column=4, value=-yb / nb)
            row += 1
        ch = ScatterChart()
        ch.title = f"{label}: {p['file']} / {p['sample_A']} vs {p['sample_B']}"
        ch.x_axis.title = "Wavelength (nm)"
        ch.y_axis.title = "归一化 g-factor"
        ch.height = 9
        ch.width = 16
        ch.style = 13
        ch.x_axis.delete = False
        ch.y_axis.delete = False
        ch.x_axis.scaling.min = 300
        ch.x_axis.scaling.max = 500
        ch.x_axis.majorUnit = 50
        ch.y_axis.number_format = "0.00"
        ch.y_axis.scaling.min = -1.0
        ch.y_axis.scaling.max = 1.0
        ch.y_axis.majorUnit = 0.25
        ch.legend.position = "r"
        rep_colors = ["1F77B4", "FF7F0E", "7F7F7F"]
        for j in range(2, 5):
            xref = Reference(ws_rep, min_col=1, min_row=first, max_row=row - 1)
            yref = Reference(ws_rep, min_col=j, min_row=first, max_row=row - 1)
            s = Series(yref, xref, title=ws_rep.cell(row=first - 1, column=j).value)
            s.marker.symbol = "none"
            s.smooth = False
            s.graphicalProperties.line.solidFill = rep_colors[(j - 2) % 3]
            s.graphicalProperties.line.width = 18000
            ch.series.append(s)
        ws.add_chart(ch, next_anchor())

    # ---------------- 13_镜像分组 ----------------
    ws = wb.create_sheet("13_镜像分组")
    headers = ["文件", "组1", "组2", "高置信", "中置信", "低置信", "总镜像边", "说明"]
    ws.append(headers)
    style_header(ws, 1, len(headers))
    for stem in file_stems:
        comps = mirror_blocks(pairs, stem)
        if not comps:
            write_row(ws, ws.max_row + 1, [stem, "—", "—", 0, 0, 0, 0, "无镜像判定对"])
            continue
        for c in comps:
            conf = c["conf"]
            base = [conf.get("高", 0), conf.get("中", 0), conf.get("低", 0), len(c["edges"])]
            if c["ok"] and len(c["nodes"]) >= 2:
                write_row(ws, ws.max_row + 1, [
                    stem, ", ".join(c["sides"][0]), ", ".join(c["sides"][1]),
                    *base, "二分：两组互为镜像",
                ])
            else:
                write_row(ws, ws.max_row + 1, [
                    stem, "—", "—", *base,
                    "非二分（存在奇数环，可能有混合/多手性）: " + ", ".join(c["nodes"]),
                ])
    set_widths(ws, [26, 34, 34, 9, 9, 9, 10, 46])
    ws.freeze_panes = "A2"

    order = ["00_说明", "01_QC", "02_配对总表", "03_相似度矩阵", "04_镜像矩阵",
             "05_位移矩阵", "06_峰位表", "07_最佳配对", "08_图表", "09_结论摘要",
             "10_谱图数据", "11_SM数据", "12_代表谱对", "13_镜像分组", "14_最佳谱对"]
    wb._sheets = sorted(wb._sheets, key=lambda s: order.index(s.title) if s.title in order else 99)
    wb.save(path)


# ----------------------------------------------------------------------
# sensitivity
# ----------------------------------------------------------------------
def mirror_blocks(pairs, stem):
    """Bipartite grouping of high/medium-confidence mirror pairs in one file.

    A clean chirality inversion across a composition series shows up as a
    complete bipartite graph: every sample in group 1 mirrors every sample
    in group 2.  Odd cycles indicate a mixed / inconsistent situation.
    """
    ps = [p for p in pairs
          if p["file"] == stem and p["decision"].startswith("镜像")]
    nodes = sorted({p["sample_A"] for p in ps} | {p["sample_B"] for p in ps},
                   key=lambda n: SAMPLE_ORDER.index(n) if n in SAMPLE_ORDER else 99)
    adj = {n: set() for n in nodes}
    for p in ps:
        adj[p["sample_A"]].add(p["sample_B"])
        adj[p["sample_B"]].add(p["sample_A"])

    seen, comps = set(), []
    for start in nodes:
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        color = {comp[0]: 0}
        ok, stack = True, [comp[0]]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in color:
                    color[v] = 1 - color[u]
                    stack.append(v)
                elif color[v] == color[u]:
                    ok = False
        edges = [(a, b) for a in comp for b in adj[a] if a < b]
        conf = Counter()
        for e in edges:
            for p in ps:
                if {p["sample_A"], p["sample_B"]} == set(e):
                    conf[p["confidence"]] += 1
                    break
        key = lambda n: SAMPLE_ORDER.index(n) if n in SAMPLE_ORDER else 99
        comp.sort(key=key)
        sides = [sorted([x for x in comp if color.get(x) == 0], key=key),
                 sorted([x for x in comp if color.get(x) == 1], key=key)]
        comps.append({"nodes": comp, "ok": ok, "sides": sides,
                      "edges": edges, "conf": conf})

    comps.sort(key=lambda c: -len(c["nodes"]))
    return comps


def threshold_sensitivity(pairs):
    base = [p["decision"] for p in pairs]
    out = []

    def count_change(overrides):
        t = dict(DEFAULT_T)
        t.update(overrides)
        n = 0
        for p, b in zip(pairs, base):
            cat = M.classify(
                p["S_deriv"], p["M_deriv"], p["dS_deriv"], p["dM_deriv"],
                p["qS"], p["qM"], min(p["snr_A"], p["snr_B"]),
                p["band_mirror"] if np.isfinite(p["band_mirror"]) else float("nan"),
                p["band_n"], t,
            )
            if cat != b:
                n += 1
        return n

    for label, ov in [
        ("S阈值 0.65", {"s": 0.65}),
        ("S阈值 0.75", {"s": 0.75}),
        ("margin 0.15", {"margin": 0.15}),
        ("margin 0.25", {"margin": 0.25}),
        ("位移阈值 2 nm", {"shift": 2.0}),
        ("位移阈值 4 nm", {"shift": 4.0}),
    ]:
        out.append((label, count_change(ov)))
    return out


# ----------------------------------------------------------------------
# self tests
# ----------------------------------------------------------------------
def run_self_tests(records):
    lines = []
    ok = True

    # 1) r(A,A)=1, r(A,-A)=-1
    rec = records[0]
    for key in ("raw", "hp", "deriv"):
        s = M.summarize_profile(M.corr_profile(rec["prep"][key], rec["prep"][key]))
        m = M.summarize_profile(M.corr_profile(rec["prep"][key], -rec["prep"][key]))
        if abs(s["S"] - 1) > 1e-6 or abs(m["M"] - 1) > 1e-6:
            ok = False
    lines.append(f"[{'PASS' if ok else 'FAIL'}] self-correlation: r(A,A)=1, r(A,-A)=-1")

    # 2) synthetic shift recovery
    x = M.GRID

    def gauss(center, sigma, amp):
        return amp * np.exp(-0.5 * ((x - center) / sigma) ** 2)

    base = gauss(340, 12, 2.0) - gauss(385, 14, 1.5) + 0.0008 * (x - 280) / 240
    p0 = M.prepare(x, base)
    errs = []
    for shift in (-12.0, -5.0, 5.0, 12.0, 20.0):
        y = gauss(340 + shift, 12, 2.0) - gauss(385 + shift, 14, 1.5) + 0.0008 * (x - 280) / 240
        p1 = M.prepare(x, y)
        sm = M.summarize_profile(M.corr_profile(p0["deriv"], p1["deriv"]))
        errs.append(abs(sm["dS"] - shift))
    ok2 = max(errs) <= 0.5
    ok = ok and ok2
    lines.append(f"[{'PASS' if ok2 else 'FAIL'}] synthetic shift recovery: max error {max(errs):.2f} nm")

    # 3) synthetic mirror
    pm = M.prepare(x, -base)
    sm = M.summarize_profile(M.corr_profile(p0["deriv"], pm["deriv"]))
    ok3 = sm["M"] >= 0.95 and abs(sm["dM"]) <= 0.5
    ok = ok and ok3
    lines.append(f"[{'PASS' if ok3 else 'FAIL'}] synthetic mirror: M={sm['M']:.3f}, delta_M={sm['dM']:+.1f} nm")

    # 4) parser / data coverage (works for any number of workbooks)
    ok4 = (len(records) >= 2 and all(r["covers_280_520"] for r in records)
           and all(r["n300"] >= 201 for r in records))
    ok = ok and ok4
    lines.append(f"[{'PASS' if ok4 else 'FAIL'}] parser: {len(records)} spectra, all cover 300-500 and 280-520 nm")

    # 5) known duplicates in the published dataset (skipped for other inputs)
    def find(stem, name):
        for r in records:
            if r["file"] == stem and r["name"] == name:
                return r
        return None

    checks = [("01_1_MPAOMe_Lcys", "03_1_MPAOMe_NAC"),
              ("01_2_MPA_Lcys", "03_2_MPA_NAC")]
    present = all(find(a, "0-16") is not None and find(b, "0-16") is not None for a, b in checks)
    if present:
        ok5 = True
        for stem_a, stem_b in checks:
            a = find(stem_a, "0-16")
            b = find(stem_b, "0-16")
            if a is None or b is None or not np.allclose(a["prep"]["raw"], b["prep"]["raw"], atol=1e-12):
                ok5 = False
        ok = ok and ok5
        lines.append(f"[{'PASS' if ok5 else 'FAIL'}] known duplicate columns: 0-16 identical across workbooks")
    else:
        lines.append("[SKIP] known duplicate-column check (dataset-specific)")

    return ok, lines


# ----------------------------------------------------------------------
# README
# ----------------------------------------------------------------------
def write_readme(path, records, pairs, file_stems, self_lines):
    cat_counts = Counter(p["decision"] for p in pairs)
    lines = []
    lines.append("# NAC 配体 CD（g-factor）谱图相似性 / 镜像相似性结果\n")
    lines.append("## 1. 数据与解析\n")
    lines.append(f"- 输入：`01_raw data/` 下 8 个 xlsx，每个 9 条谱图，共 **{len(records)}** 条。")
    lines.append("- 只做**同一 Excel 内** 9 条谱图的两两比较：每个文件 36 对，共 **288 对**；不做跨文件比较。")
    lines.append("- 自动识别两种列布局（共享波长列 / 每样品一对 wavelength+g-factor），跳过 JASCO 元数据与文本单元格。")
    lines.append("- 统一到 280–520 nm / 0.5 nm 网格；比较窗口 300–500 nm；位移 ±20 nm 不需要外推。")
    lines.append("- 端元：`16-0` = 纯 thiol2，`0-16` = 纯 thiol1；纳入比较并单独标记。\n")
    lines.append("## 2. 方法\n")
    lines.append("| 项目 | 设置 |")
    lines.append("|---|---|")
    lines.append("| 相似性 | Pearson r（主）、余弦/SAM、NRMSE（辅） |")
    lines.append("| 位移 | 全局刚体 δ∈[−20,+20] nm，步长 0.5 nm；S=max r，M=max(−r) |")
    lines.append("| 三套表示 | raw、high-pass（减 30 nm SG 背景）、一阶导数（10.5 nm SG） |")
    lines.append("| 镜像 | A vs −B；镜像指数 (M−S)/(M+S) |")
    lines.append(f"| 显著性 | 相位随机化 surrogate {N_SUR} 次；文件内 BH-FDR |")
    lines.append("| 判定 | S/M≥0.70，margin≥0.20，位移≥3 nm，SNR≥20，q<0.05；镜像需带级 mirror 一致率≥0.60（带数≥2） |")
    lines.append("| 带级 | prominence≥3×局部噪声、宽度≥4 nm 的前 4 个极值；|Δλ|≤20 nm 最优配对 |\n")
    lines.append("## 3. 总体结果\n")
    lines.append("| 判定 | 对数 | 占比 |")
    lines.append("|---|---:|---:|")
    for c in CATEGORIES:
        n = cat_counts.get(c, 0)
        lines.append(f"| {c} | {n} | {n/len(pairs)*100:.1f}% |")
    lines.append("")
    lines.append("### 3.1 镜像分组（所有镜像判定边；高/中/低为置信度）\n")
    lines.append("| 文件 | 组1 | 组2 | 高 | 中 | 低 | 总镜像边 |")
    lines.append("|---|---|---|---:|---:|---:|---:|")
    for stem in file_stems:
        ps = [p for p in pairs if p["file"] == stem]
        comps = mirror_blocks(ps, stem)
        if not comps:
            lines.append(f"| {stem} | — | — | 0 | 0 | 0 | 0 |")
            continue
        for c in comps:
            conf = c["conf"]
            if c["ok"]:
                lines.append(f"| {stem} | {'、'.join(c['sides'][0])} | {'、'.join(c['sides'][1])} "
                             f"| {conf.get('高', 0)} | {conf.get('中', 0)} | {conf.get('低', 0)} | {len(c['edges'])} |")
            else:
                lines.append(f"| {stem} | 非二分 | {'、'.join(c['nodes'])} "
                             f"| {conf.get('高', 0)} | {conf.get('中', 0)} | {conf.get('低', 0)} | {len(c['edges'])} |")
    lines.append("")
    lines.append("### 3.2 主要观察\n")
    mir_n = {stem: sum(1 for p in pairs if p["file"] == stem and p["decision"].startswith("镜像"))
             for stem in file_stems}
    same_n = {stem: sum(1 for p in pairs if p["file"] == stem and p["decision"].startswith("同手性"))
              for stem in file_stems}
    top_mir = sorted(file_stems, key=lambda s: -mir_n[s])
    no_mir = [s for s in file_stems if mir_n[s] == 0]
    top_same = sorted(file_stems, key=lambda s: -same_n[s])
    lines.append(f"- 镜像判定对最多的文件：{top_mir[0]}（{mir_n[top_mir[0]]} 对）；"
                 f"其次 " + "、".join(f"{s}（{mir_n[s]}）" for s in top_mir[1:4]) + "。")
    lines.append(f"- 未检出镜像判定对的文件：{('、'.join(no_mir)) if no_mir else '无'}。")
    lines.append(f"- 同手性判定对最多的文件：{top_same[0]}（{same_n[top_same[0]]} 对）；"
                 f"其次是 " + "、".join(f"{s}（{same_n[s]}）" for s in top_same[1:3]) + "。")
    lines.append("- “无镜像判定对”只表示未达到当前阈值，不等于物理上不存在翻转；需结合 SNR、判定置信度和原始谱看。\n")
    for stem in file_stems:
        ps = [p for p in pairs if p["file"] == stem]
        cnt = Counter(p["decision"] for p in ps)
        lines.append(f"### {stem}\n")
        lines.append("| 判定 | 对数 |")
        lines.append("|---|---:|")
        for c in CATEGORIES:
            if cnt.get(c, 0):
                lines.append(f"| {c} | {cnt[c]} |")
        top_s = sorted(ps, key=lambda p: -p["S_deriv"])[:3]
        top_m = sorted(ps, key=lambda p: -p["M_deriv"])[:3]
        lines.append("\n最相似：" + "；".join(
            f"{p['sample_A']}–{p['sample_B']} (S={p['S_deriv']:.2f}, δ={p['dS_deriv']:+.1f} nm)"
            for p in top_s))
        lines.append("\nM 最高（不一定是判定镜像）：" + "；".join(
            f"{p['sample_A']}–{p['sample_B']} (M={p['M_deriv']:.2f}, δ={p['dM_deriv']:+.1f} nm, {p['decision']})"
            for p in top_m))
        comps = mirror_blocks(ps, stem)
        if comps:
            c = comps[0]
            conf = c["conf"]
            if c["ok"]:
                lines.append(f"\n镜像二分：{'、'.join(c['sides'][0])} ↔ {'、'.join(c['sides'][1])}"
                             f"（高/中/低 = {conf.get('高', 0)}/{conf.get('中', 0)}/{conf.get('低', 0)} 条边）")
            else:
                lines.append(f"\n镜像关系非二分：{'、'.join(c['nodes'])}（可能有混合/多手性）")
        lines.append("")
    lines.append("## 4. 限制与注意事项\n")
    lines.append("- g-factor = Δε/ε。可区分“镜像（符号翻转）”与“非镜像（形状/位移改变）”，但只有 g 谱时不能把非镜像变化唯一归因于 CD 带位移或吸收带位移。")
    lines.append("- 420–500 nm 存在共同抬升背景；raw 相关会偏高，判定以去背景（导数）指标为主，三套指标冲突时标为低置信。")
    lines.append("- 位移最优落在 ±20 nm 边界时只表示“≥20 nm 或无明确位移”，不是精确值。")
    lines.append("- 低 SNR 谱对不参与强判定。")
    lines.append("- “主带”是平滑后 |g| 最大的极值；对弱谱/端元样品可能是背景尾而非 Cotton 带。")
    lines.append("- `01_2` / `03_2` 的 `0-16` 列在 580.5 nm 有异常尖峰，位于窗口外，不影响结果。")
    lines.append("- 端元样品（纯 thiol1 / 纯 thiol2）不是混合物，解释时需单独看。\n")
    lines.append("## 5. 复现\n")
    lines.append("```bash")
    lines.append('python 02_analysis/cd_compare.py --input "01_raw data" --out "02_analysis/out"')
    lines.append("```\n")
    lines.append("## 6. 自检\n")
    for l in self_lines:
        lines.append(f"- {l}")
    path.write_text("\n".join(lines), encoding="utf-8")


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="../01_raw data")
    ap.add_argument("--out", default="out")
    ap.add_argument("--surrogates", type=int, default=N_SUR)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args(argv)

    in_dir = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(in_dir.glob("*.xlsx"))
    if not files:
        print(f"No xlsx in {in_dir}", file=sys.stderr)
        return 1

    t0 = time.time()
    records = []
    file_stems = []
    for path in files:
        stem = path.stem
        file_stems.append(stem)
        samples = read_cd_workbook(path)
        if len(samples) != 9:
            print(f"WARNING: {stem} has {len(samples)} samples (expected 9)")
        for s in samples:
            records.append(build_record(stem, s))
        print(f"  {stem}: {len(samples)} samples")
    print(f"Parsed {len(records)} spectra in {time.time()-t0:.1f}s")

    ok, self_lines = run_self_tests(records)
    for l in self_lines:
        print(l)

    rng = np.random.default_rng(args.seed)
    pairs = []
    for stem in file_stems:
        recs = [r for r in records if r["file"] == stem]
        ps = compute_pairs(recs, rng, args.surrogates)
        pairs.extend(ps)
        print(f"  {stem}: {len(ps)} pairs done  ({time.time()-t0:.0f}s)")
    finalize_pairs(pairs)
    print(f"All pairs done in {time.time()-t0:.0f}s")

    # CSVs
    import csv
    pair_cols = [k for k in pairs[0] if not k.startswith("_")]
    with open(out_dir / "pairwise_metrics.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=pair_cols, extrasaction="ignore")
        w.writeheader()
        for p in pairs:
            w.writerow({k: _v(p[k]) for k in pair_cols})

    qc_cols = ["file", "name", "endpoint", "n", "wmin", "wmax", "step", "n300",
               "covers_280_520", "amp", "noise", "snr", "spikes",
               "dom_lam", "dom_sign", "dom_amp"]
    with open(out_dir / "qc_spectra.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=qc_cols, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow({k: _v(r[k]) for k in qc_cols})

    # Excel + README
    xlsx_path = out_dir / "CD_similarity_results.xlsx"
    build_excel(xlsx_path, records, pairs, file_stems, ok, self_lines)
    write_readme(out_dir / "README_方法与结果.md", records, pairs, file_stems, self_lines)
    print(f"Wrote {xlsx_path} and README in {time.time()-t0:.0f}s")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
