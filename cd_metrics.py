"""Numerical core for CD (g-factor) spectral comparison.

Pure numpy: no scipy / matplotlib dependency.

All spectra are resampled onto a common grid of 280-520 nm at 0.5 nm
(481 points).  Comparisons are made on the 300-500 nm window (401
points).  Because the grid is padded by 20 nm on both sides, a spectral
shift of +/-20 nm never requires extrapolation:  the shifted spectrum is
read from its own 280-520 nm data.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# ----------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------
DX = 0.5
GRID = np.arange(280.0, 520.0 + 1e-9, DX)      # 481 points
N_GRID = len(GRID)

WIN_START = int(round((300.0 - 280.0) / DX))    # 40
NWIN = int(round((500.0 - 300.0) / DX)) + 1     # 401

SHIFT_STEPS = np.arange(-40, 41)                # +/-20 nm in 0.5 nm units
SHIFTS_NM = SHIFT_STEPS * DX
N_SHIFT = len(SHIFT_STEPS)

DEFAULT_THRESHOLDS = {
    "s": 0.70,          # S or M must reach this
    "margin": 0.20,     # S - M (or M - S) must reach this
    "shift": 3.0,       # nm ; below this the pair is "coincident"
    "snr": 20.0,        # per-spectrum amplitude / noise
    "q": 0.05,          # FDR-adjusted surrogate p-value
    "band_mirror": 0.60,
}


# ----------------------------------------------------------------------
# Savitzky-Golay
# ----------------------------------------------------------------------
def sg_coeffs(window: int, order: int, deriv: int = 0, dx: float = DX) -> np.ndarray:
    """Return SG convolution coefficients for a centred window."""
    if window % 2 == 0:
        window += 1
    half = window // 2
    x = np.arange(-half, half + 1) * dx
    V = np.vander(x, order + 1, increasing=True)
    return np.linalg.pinv(V)[deriv] * math.factorial(deriv)


def sg_filter(y: np.ndarray, window: int, order: int, deriv: int = 0) -> np.ndarray:
    """Savitzky-Golay smoothing / differentiation with reflect padding."""
    y = np.asarray(y, float)
    k = sg_coeffs(window, order, deriv)
    half = (len(k) - 1) // 2
    if half == 0:
        return y.copy()
    ypad = np.pad(y, half, mode="reflect")
    win = np.lib.stride_tricks.sliding_window_view(ypad, len(k))
    return win @ k


# ----------------------------------------------------------------------
# preprocessing
# ----------------------------------------------------------------------
def prepare(W: Sequence[float], G: Sequence[float]) -> Dict[str, np.ndarray]:
    """Sort, resample and build the three representations used below."""
    W = np.asarray(W, float)
    G = np.asarray(G, float)
    order = np.argsort(W)
    W, G = W[order], G[order]
    y = np.interp(GRID, W, G)

    raw = sg_filter(y, 11, 2)                       # 5.5 nm smoothing
    hp = raw - sg_filter(raw, 61, 2)                # remove > ~30 nm background
    der = sg_filter(raw, 21, 2, deriv=1)            # 10.5 nm first derivative
    return {"raw": raw, "hp": hp, "deriv": der, "interp": y}


def qc_stats(y: np.ndarray) -> Dict[str, float]:
    """Amplitude, high-frequency noise and SNR of one spectrum."""
    y = np.asarray(y, float)
    smooth = sg_filter(y, 11, 2)
    resid = y - smooth
    noise = 1.4826 * np.median(np.abs(resid - np.median(resid)))
    amp = float(np.percentile(smooth, 98) - np.percentile(smooth, 2))
    noise = float(max(noise, 1e-15))
    return {"amp": amp, "noise": noise, "snr": amp / noise}


# ----------------------------------------------------------------------
# similarity profiles
# ----------------------------------------------------------------------
def _window(y: np.ndarray) -> np.ndarray:
    return np.asarray(y, float)[WIN_START:WIN_START + NWIN]


def shift_matrix(B: np.ndarray) -> np.ndarray:
    """(81, 401) matrix of B shifted by every delta in SHIFTS_NM.

    Row j is B( lambda + SHIFTS_NM[j] ) evaluated on the 300-500 nm grid.
    """
    B = np.asarray(B, float)
    idx = np.arange(NWIN)
    return B[WIN_START + SHIFT_STEPS[:, None] + idx]


def corr_profile(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Pearson r between A and B(lambda+delta) for all deltas."""
    a = _window(A)
    bm = shift_matrix(B)
    ac = a - a.mean()
    an = np.linalg.norm(ac)
    bmc = bm - bm.mean(axis=1, keepdims=True)
    bn = np.linalg.norm(bmc, axis=1)
    out = np.full(N_SHIFT, np.nan)
    ok = (bn > 0) & (an > 0)
    out[ok] = (bmc[ok] @ ac) / (bn[ok] * an)
    return out


def cosine_profile(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Cosine similarity between A and shifted B."""
    a = _window(A)
    bm = shift_matrix(B)
    an = np.linalg.norm(a)
    bn = np.linalg.norm(bm, axis=1)
    out = np.full(N_SHIFT, np.nan)
    ok = (bn > 0) & (an > 0)
    out[ok] = (bm[ok] @ a) / (bn[ok] * an)
    return out


def nrmse_profile(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """NRMSE after unit-RMS normalisation, for all deltas."""
    a = _window(A)
    bm = shift_matrix(B)
    a0 = a / (np.sqrt(np.mean(a * a)) + 1e-15)
    b0 = bm / (np.sqrt(np.mean(bm * bm, axis=1, keepdims=True)) + 1e-15)
    return np.sqrt(np.mean((b0 - a0) ** 2, axis=1))


def summarize_profile(r: np.ndarray) -> Dict[str, float]:
    """S / delta_S / M / delta_M / r at zero shift."""
    r = np.asarray(r, float)
    i = int(np.nanargmax(r))
    j = int(np.nanargmin(r))
    return {
        "S": float(r[i]),
        "dS": float(SHIFTS_NM[i]),
        "M": float(-r[j]),
        "dM": float(SHIFTS_NM[j]),
        "r0": float(r[N_SHIFT // 2]),
    }


# ----------------------------------------------------------------------
# surrogate null distribution
# ----------------------------------------------------------------------
def phase_randomize(y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Randomise Fourier phases, preserving the power spectrum."""
    y = np.asarray(y, float)
    n = len(y)
    Y = np.fft.rfft(y - y.mean())
    ph = rng.uniform(0.0, 2.0 * np.pi, len(Y))
    ph[0] = 0.0
    if n % 2 == 0:
        ph[-1] = 0.0
    Ys = np.abs(Y) * np.exp(1j * ph)
    return np.fft.irfft(Ys, n) + y.mean()


def surrogate_maxima(
    A: np.ndarray,
    B: np.ndarray,
    n_sur: int,
    rng: np.random.Generator,
    batch: int = 500,
) -> Tuple[np.ndarray, np.ndarray]:
    """Null distributions of max_delta r and max_delta (-r).

    Phase-randomised surrogates of B preserve its power spectrum (and
    therefore its smoothness) but destroy the alignment with A.  Batched
    to keep memory bounded for n_sur of a few thousand.
    """
    a = _window(A)
    ac = a - a.mean()
    an = np.linalg.norm(ac)
    idx = np.arange(NWIN)
    s_parts: List[np.ndarray] = []
    m_parts: List[np.ndarray] = []
    done = 0
    while done < n_sur:
        nb = min(batch, n_sur - done)
        sur = np.stack([phase_randomize(B, rng) for _ in range(nb)])
        big = sur[:, WIN_START + SHIFT_STEPS[:, None] + idx]  # (nb, 81, 401)
        big = big - big.mean(axis=2, keepdims=True)
        bn = np.linalg.norm(big, axis=2)
        r = np.einsum("swn,n->sw", big, ac) / (bn * an + 1e-15)
        s_parts.append(r.max(axis=1))
        m_parts.append((-r).max(axis=1))
        done += nb
    return np.concatenate(s_parts), np.concatenate(m_parts)


# ----------------------------------------------------------------------
# Cotton band detection / matching
# ----------------------------------------------------------------------
def find_bands(
    g: np.ndarray,
    x: np.ndarray = GRID,
    smooth_window: int = 21,
    min_prom_frac: float = 3.0,
    min_width_nm: float = 4.0,
    max_bands: int = 4,
) -> List[Dict[str, float]]:
    """Local extrema with enough prominence and width."""
    g = np.asarray(g, float)
    y = sg_filter(g, smooth_window, 2)
    resid = g - y
    n = len(y)
    cand: List[Dict[str, float]] = []

    for i in range(2, n - 2):
        is_peak = y[i] > y[i - 1] and y[i] >= y[i + 1]
        is_trough = y[i] < y[i - 1] and y[i] <= y[i + 1]
        if not (is_peak or is_trough):
            continue

        lo, hi = max(0, i - 40), min(n, i + 41)
        seg = resid[lo:hi]
        noise = 1.4826 * np.median(np.abs(seg - np.median(seg)))
        noise = max(float(noise), 1e-15)

        sign = 1.0 if is_peak else -1.0
        z = sign * y

        lmin = z[i]
        j = i - 1
        while j >= 0 and z[j] < z[i]:
            lmin = min(lmin, z[j])
            j -= 1
        rmin = z[i]
        j = i + 1
        while j < n and z[j] < z[i]:
            rmin = min(rmin, z[j])
            j += 1
        prom = z[i] - max(lmin, rmin)
        if prom < min_prom_frac * noise:
            continue

        half = z[i] - 0.5 * prom
        left: Optional[float] = None
        for j in range(i, 0, -1):
            if (z[j - 1] - half) * (z[j] - half) <= 0 and z[j] != z[j - 1]:
                left = x[j - 1] + (half - z[j - 1]) * (x[j] - x[j - 1]) / (z[j] - z[j - 1])
                break
        if left is None:
            left = x[0]
        right: Optional[float] = None
        for j in range(i, n - 1):
            if (z[j] - half) * (z[j + 1] - half) <= 0 and z[j + 1] != z[j]:
                right = x[j] + (half - z[j]) * (x[j + 1] - x[j]) / (z[j + 1] - z[j])
                break
        if right is None:
            right = x[-1]
        width = abs(right - left)

        if width < min_width_nm:
            continue

        cand.append(
            {
                "lam": float(x[i]),
                "amp": float(y[i]),
                "prom": float(prom),
                "sign": sign,
                "width": float(width),
            }
        )

    cand.sort(key=lambda d: -d["prom"])
    cand = cand[:max_bands]
    cand.sort(key=lambda d: d["lam"])
    return cand


def match_bands(
    pa: List[Dict[str, float]],
    pb: List[Dict[str, float]],
    max_dl: float = 20.0,
) -> Dict[str, float]:
    """One-to-one band matching, maximising count then minimising distance."""
    best: Dict[str, object] = {"pairs": [], "score": None}

    def rec(i: int, used: set, pairs: list, dist: float) -> None:
        if i == len(pa):
            score = (len(pairs), -dist)
            if best["score"] is None or score > best["score"]:  # type: ignore[operator]
                best["pairs"] = list(pairs)
                best["score"] = score
            return
        rec(i + 1, used, pairs, dist)
        for j in range(len(pb)):
            if j in used:
                continue
            dl = abs(pa[i]["lam"] - pb[j]["lam"])
            if dl <= max_dl:
                used.add(j)
                pairs.append((pa[i], pb[j]))
                rec(i + 1, used, pairs, dist + dl)
                pairs.pop()
                used.remove(j)

    rec(0, set(), [], 0.0)
    pairs = best["pairs"]  # type: ignore[assignment]

    if not pairs:
        return {
            "n": 0.0,
            "same": float("nan"),
            "mirror": float("nan"),
            "median_dl": float("nan"),
        }

    w = np.array([min(abs(a["amp"]), abs(b["amp"])) for a, b in pairs], float)
    same = np.array([1.0 if a["sign"] == b["sign"] else 0.0 for a, b in pairs], float)
    dl = np.array([b["lam"] - a["lam"] for a, b in pairs], float)
    wsum = w.sum() if w.sum() > 0 else 1.0
    return {
        "n": float(len(pairs)),
        "same": float((w * same).sum() / wsum),
        "mirror": float((w * (1.0 - same)).sum() / wsum),
        "median_dl": float(np.median(dl)),
    }


# ----------------------------------------------------------------------
# statistics / decision
# ----------------------------------------------------------------------
def bh_fdr(p: Sequence[float]) -> np.ndarray:
    """Benjamini-Hochberg FDR (nan-safe)."""
    p = np.asarray(p, float)
    out = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    if not ok.any():
        return out
    pv = p[ok]
    n = len(pv)
    order = np.argsort(pv)
    ranked = pv[order]
    q = ranked * n / (np.arange(n) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0.0, 1.0)
    tmp = np.empty(n)
    tmp[order] = q
    out[ok] = tmp
    return out


def classify(
    S: float,
    M: float,
    dS: float,
    dM: float,
    qS: float,
    qM: float,
    snr_min: float,
    band_mirror: float,
    n_matched: float,
    thresholds: Optional[Dict[str, float]] = None,
) -> str:
    """Assign a pair to one of the six decision categories."""
    t = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        t.update(thresholds)

    if not np.isfinite(S) or not np.isfinite(M):
        return "弱/不可判定"
    if snr_min < t["snr"]:
        return "弱/不可判定"

    if S >= t["s"] and (S - M) >= t["margin"] and qS < t["q"]:
        if abs(dS) < t["shift"]:
            return "同手性·高度一致"
        return "同手性·位移型"

    if M >= t["s"] and (M - S) >= t["margin"] and qM < t["q"]:
        if n_matched >= 2 and np.isfinite(band_mirror) and band_mirror < t["band_mirror"]:
            return "弱/不可判定"
        if abs(dM) >= t["shift"]:
            return "镜像+位移"
        return "镜像·手性翻转"

    if max(S, M) < 0.40:
        return "不相似"
    return "弱/不可判定"


def coarse(category: str) -> str:
    if category.startswith("同手性"):
        return "same"
    if category.startswith("镜像"):
        return "mirror"
    return "none"
