# Supplementary Methods

## Quantitative comparison of circular dichroism g-factor spectra: similarity, mirror-image similarity and wavelength-shift analysis

### S1. Overview of the workflow

The analysis takes the g-factor spectra exported from the spectropolarimeter as input and compares every pair of samples within a single workbook. For each pair it returns (i) a same-sense similarity score, (ii) a mirror-image similarity score, (iii) the optimal rigid wavelength shifts for the two hypotheses, (iv) Cotton-band sign concordance and position differences, (v) surrogate-based significance values, and (vi) a decision class with a confidence score. The same workflow is used for all workbooks; no comparisons are made between different workbooks.

### S2. Data export and curation

Circular dichroism (CD) spectra were recorded on a JASCO J-1500 spectropolarimeter. The g-factor, defined as

$$g=\frac{\Delta\varepsilon}{\varepsilon},$$

where $\Delta\varepsilon$ and $\varepsilon$ are the molar CD and molar extinction coefficients, was exported from the instrument software as a function of wavelength. For a conventional CD measurement, $g$ is related to the measured ellipticity $\theta$ (mdeg) and the absorbance $A$ by $g=\theta/(32980A)$; the exported g-factor was used directly without further conversion.

Raw exports covered 200–600 nm (some samples 200–520, 200–550 or 200–650 nm) at 0.5 or 1 nm intervals. Each workbook contains nine samples labelled $X$–$Y$, where $X$ and $Y$ are the nominal amounts of thiol2 and thiol1, respectively; $X$–0 and 0–$Y$ are single-ligand end members. Only the 300–500 nm window was analysed. Two export layouts were parsed automatically: (i) interleaved columns of wavelength and g-factor for each sample, and (ii) a single shared wavelength column followed by one g-factor column per sample. Rows containing instrument metadata (for example "Scanning speed", "Baseline correction") were discarded; only rows in which both wavelength and g-factor were numeric were retained. Within each workbook the nine spectra were compared pairwise, giving 36 pairs per workbook; the eight workbooks of the present dataset give 288 pairs in total.

Sample labels were parsed as $X$–$Y$, with $X$–0 identified as the pure thiol2 end member, 0–$Y$ as the pure thiol1 end member and all other labels as mixtures. End-member spectra were included in the pairwise comparison but were flagged in all output tables, because they are single-ligand references rather than mixtures.

### S3. Preprocessing and spectral representations

For each spectrum, wavelengths were sorted in ascending order and duplicate wavelengths were averaged. The g-factor trace was linearly interpolated onto a common grid of 280–520 nm with a 0.5 nm step (481 points). The 20 nm padding on each side of the 300–500 nm analysis window allows a rigid shift of up to ±20 nm to be evaluated without truncating the comparison window or extrapolating beyond the measured range.

Three representations were generated with Savitzky–Golay (SG) filters:

1. **raw**: SG smoothing with an 11-point window (5.5 nm) and a second-order polynomial;
2. **high-pass**: raw minus an SG-smoothed baseline with a 61-point window (approximately 30 nm);
3. **first derivative**: SG differentiation with a 21-point window (approximately 10.5 nm) and a second-order polynomial.

The high-pass and derivative representations suppress the slowly varying background shared by all samples, most notably the monotonic rise between 420 and 500 nm, and emphasize the positions and signs of the Cotton bands. Raw correlations are reported for transparency but were not used as the primary decision variable, because they can be dominated by the common background. Pearson and cosine similarities are invariant to multiplicative scaling, so no amplitude normalization was applied for those metrics; for the normalized root-mean-square error (NRMSE), each spectrum was normalized to unit RMS.

### S4. Similarity and wavelength-shift search

Let $A(\lambda)$ and $B(\lambda)$ be two g-factor spectra on the 300–500 nm window. For a rigid shift $\delta$, define $B_\delta(\lambda)=B(\lambda+\delta)$; $\delta>0$ corresponds to a red shift of $B$ relative to $A$. The Pearson correlation is

$$r_{AB}(\delta)=\frac{\sum_i\left[A(\lambda_i)-\bar A\right]\left[B(\lambda_i+\delta)-\bar B_\delta\right]}{\sqrt{\sum_i\left[A(\lambda_i)-\bar A\right]^2}\sqrt{\sum_i\left[B(\lambda_i+\delta)-\bar B_\delta\right]^2}},$$

where $\lambda_i$ runs over the 401 grid points and $\bar A$ and $\bar B_\delta$ are the corresponding means. The same-sense score and optimal shift are

$$S=\max_{\delta\in[-20,20]\,\mathrm{nm}}r_{AB}(\delta),\qquad \delta_S=\arg\max_{\delta}r_{AB}(\delta).$$

The shift grid was −20 to +20 nm in 0.5 nm steps (81 values). Cosine similarity, spectral angle mapper (SAM; $\mathrm{SAM}=\arccos(\cos\theta)$) and NRMSE after unit-RMS normalization were computed on the same grid as complementary metrics.

### S5. Mirror-image similarity

A mirror-image CD spectrum has $\Delta\varepsilon\to-\Delta\varepsilon$ with $\varepsilon$ unchanged, so that $g\to-g$. Mirror similarity was therefore assessed by comparing $A$ with $-B$:

$$M=\max_{\delta\in[-20,20]\,\mathrm{nm}}\left[-r_{AB}(\delta)\right]=-\min_{\delta}r_{AB}(\delta),\qquad \delta_M=\arg\min_{\delta}r_{AB}(\delta).$$

The mirror margin $\Delta=M-S$ and the normalized mirror index

$$I=\frac{M-S}{M+S}\in[-1,1]$$

were used to decide whether the mirror hypothesis outperforms the same-sense hypothesis. $M$ is not an independent statistic: it is the negative of the minimum of the same cross-correlation function. Reporting $S$, $M$, $\delta_S$ and $\delta_M$ separately therefore separates the sign question (mirror versus same sense) from the shift question (red or blue shift).

### S6. Cotton-band analysis

Cotton bands were detected on the SG-smoothed trace as local maxima and minima with a prominence of at least 3× the local high-frequency noise and a width at half prominence of at least 4 nm. The local noise was estimated as $1.4826\times\mathrm{MAD}$ of the residual after 21-point SG smoothing in a ±20 nm window. The four most prominent bands of each spectrum were retained.

Bands from $A$ and $B$ were matched one-to-one within $|\Delta\lambda|\le20$ nm by exhaustive search, first maximizing the number of matched bands and then minimizing the total $|\Delta\lambda|$. For matched bands $i$, the amplitude-weighted sign concordance was computed as

$$f_{\mathrm{same}}=\frac{\sum_i w_i\,\mathbf{1}\left[\mathrm{sgn}(g_{A,i})=\mathrm{sgn}(g_{B,i})\right]}{\sum_i w_i},\qquad f_{\mathrm{mirror}}=1-f_{\mathrm{same}},$$

with $w_i=\min(|g_{A,i}|,|g_{B,i}|)$. The median $\Delta\lambda$ of matched bands provided an independent estimate of the rigid shift. Band-level evidence was used as a consistency check and, when at least two bands were matched, as a requirement for mirror calls ($f_{\mathrm{mirror}}\ge0.60$).

### S7. Statistical significance

CD spectra are smooth, so adjacent wavelengths are strongly correlated and naive p-values are anti-conservative; searching 81 shifts further inflates the maximum correlation. We therefore used phase-randomized surrogates of $B$: the Fourier phases of $B$ were randomized while preserving its power spectrum, and hence its smoothness, and $S$ and $M$ were recomputed for each surrogate. $N_{\mathrm{surr}}=2000$ surrogates were used. Empirical p-values were

$$p_S=\frac{1+\#\left\{S_{\mathrm{surr}}\ge S_{\mathrm{obs}}\right\}}{1+N_{\mathrm{surr}}},\qquad p_M=\frac{1+\#\left\{M_{\mathrm{surr}}\ge M_{\mathrm{obs}}\right\}}{1+N_{\mathrm{surr}}}.$$

The Benjamini–Hochberg procedure was applied within each workbook (36 tests per workbook) at a false-discovery rate of $q<0.05$. This controls the FDR for the comparisons within a workbook without imposing the much stronger penalty of a global correction across all 288 pairs.

### S8. Decision rules and quality control

The parameters are summarized in Supplementary Table S1. A pair was classified as:

- **same-sense, high similarity**: $S\ge0.70$, $S-M\ge0.20$, $|\delta_S|<3$ nm and $q_S<0.05$;
- **same-sense, shifted**: $S\ge0.70$, $S-M\ge0.20$ and $3\le|\delta_S|\le20$ nm;
- **mirror**: $M\ge0.70$, $M-S\ge0.20$, $q_M<0.05$ and $f_{\mathrm{mirror}}\ge0.60$ when at least two bands were matched;
- **mirror plus shift**: the mirror criteria and $|\delta_M|\ge3$ nm;
- **weak/undetermined**: SNR < 20, or $\max(S,M)<0.70$, or $|M-S|<0.20$, or conflicting conclusions from the raw, high-pass and derivative representations;
- **dissimilar**: $\max(S,M)<0.40$ with no significant correlation.

The signal-to-noise ratio (SNR) of a spectrum was defined as $(\mathrm{P98}-\mathrm{P2})/\sigma$, where P98 and P2 are the 98th and 2nd percentiles of the smoothed g-factor trace and $\sigma$ is the high-frequency noise estimated from the residual after 11-point SG smoothing. For each pair, confidence was scored as high when the raw, high-pass and derivative representations gave the same coarse class (same-sense, mirror or neither), medium when the derivative agreed with one of the other two, and low otherwise, or when both $q_S$ and $q_M$ exceeded 0.05, SNR < 20, or fewer than two bands were matched. Weak and dissimilar calls were assigned low confidence by default.

The significance gate was applied to the derivative-based classification; the raw and high-pass classifications used the same effect-size thresholds and were used for confidence scoring. Shifts reaching the ±20 nm boundary were flagged as "≥20 nm or no resolvable shift" rather than reported as precise values. Isolated spikes in the raw exports were detected but did not affect the analysis, because the spectra were smoothed before comparison.

Threshold sensitivity was assessed by varying the S/M threshold by ±0.05, the margin by ±0.05 and the shift threshold between 2 and 4 nm. Across the 288 pairs, these changes altered the class of 0–15 pairs (≤5.2%), indicating that the main conclusions are not sensitive to the exact thresholds.

### S9. Software

The analysis was implemented in Python 3.12.14 using NumPy 2.3.5 and openpyxl 3.1.5. Savitzky–Golay filtering, peak detection, phase randomization, the Benjamini–Hochberg procedure and all similarity metrics were implemented in NumPy; no commercial or closed-source software was used for the analysis. The random seed was 20261114, and the full 288-pair analysis with 2000 surrogates takes about 90 s on a laptop computer.

### S10. Code and data availability

**Code availability.** The complete analysis pipeline, including workbook parsing, preprocessing, shift-search similarity and mirror metrics, Cotton-band matching, surrogate-based significance testing and generation of all tables, is available at

`https://github.com/USERNAME/cd-gfactor-similarity`

(version 1.0.0) and is archived at

`https://doi.org/10.5281/zenodo.XXXXXXX`.

The repository includes the analysis code, a synthetic demo dataset in both export layouts, unit tests and a step-by-step README.

**Data availability.** The CD g-factor data that support the findings of this study are provided as Source Data with this paper. The synthetic demo dataset used to test the code is included in the code repository.

### S11. Limitations

The analysis uses the g-factor, $g=\Delta\varepsilon/\varepsilon$. A change in $\varepsilon$, for example an absorption red or blue shift, can change $g$ even when $\Delta\varepsilon$ does not change sign; conversely, a mirror-image g-factor spectrum is strong evidence for a change in the sign of $\Delta\varepsilon$, but it is not by itself a proof of absolute configuration. Assigning the observed spectral changes to a specific molecular origin requires independent structural information and, ideally, time-dependent density functional theory (TD-DFT) calculations of the CD spectra. The thresholds in Supplementary Table S1 are operational and were chosen before the analysis; weak signals, shifts at the ±20 nm boundary, and pairs with fewer than two matched bands are flagged rather than forced into a class.

---

### Supplementary Table S1. Analysis parameters

| Parameter | Value |
|---|---|
| Analysis window | 300–500 nm |
| Common grid | 280–520 nm, 0.5 nm (481 points) |
| SG smoothing | 11 points (5.5 nm), 2nd order |
| High-pass baseline | 61 points (approximately 30 nm) |
| Derivative | 21 points (approximately 10.5 nm), 1st order |
| Shift search | −20 to +20 nm, 0.5 nm steps (81 values) |
| Similarity metrics | Pearson r (primary), cosine/SAM, NRMSE |
| Mirror transform | A versus −B |
| Surrogates | 2000 phase-randomized |
| Multiple testing | Benjamini–Hochberg, within workbook, q < 0.05 |
| S/M threshold | 0.70 |
| Margin threshold | 0.20 |
| Shift threshold | 3 nm |
| SNR threshold | 20 |
| Band prominence | 3× local noise |
| Band width (half prominence) | ≥4 nm |
| Maximum bands per spectrum | 4 |
| Band mirror concordance | ≥0.60 (when at least two bands matched) |
| Random seed | 20261114 |

### Supplementary Table S2. Columns of the pairwise output table

| Column | Meaning |
|---|---|
| `S_raw`, `S_hp`, `S_d` | Same-sense score $S$ from the raw, high-pass and derivative representations |
| `dS_raw`, `dS_hp`, `dS_d` | Optimal same-sense shift $\delta_S$ (nm) for each representation |
| `M_raw`, `M_hp`, `M_d` | Mirror score $M$ for each representation |
| `dM_raw`, `dM_hp`, `dM_d` | Optimal mirror shift $\delta_M$ (nm) for each representation |
| `r0_d` | Pearson correlation at zero shift (derivative representation) |
| `margin_d` | $M-S$ (derivative representation) |
| `mirror_index` | $(M-S)/(M+S)$ |
| `pS`, `pM` | Empirical surrogate p-values for $S$ and $M$ |
| `qS`, `qM` | Benjamini–Hochberg adjusted p-values within the workbook |
| `band_n` | Number of matched Cotton bands |
| `band_same`, `band_mirror` | Amplitude-weighted same-sign and mirror-sign concordance |
| `band_median_dl` | Median band-position difference (nm) |
| `snr_A`, `snr_B` | SNR of the two spectra |
| `decision` | Final class (same-sense high similarity / same-sense shifted / mirror / mirror plus shift / weak / dissimilar) |
| `confidence` | High, medium or low, from cross-representation agreement and data-quality flags |
| `notes` | Boundary shifts, low SNR, insufficient band evidence, metric conflicts, end-member flags |

*Note: in `pairwise_metrics.csv` the derivative columns are named `S_deriv`, `M_deriv`, `dS_deriv` and `dM_deriv`; the Excel table abbreviates them as `S_d`, `M_d`, `δS_d` and `δM_d`.*

---

*Placeholders to replace before submission: the GitHub user name, the repository URL, the Zenodo DOI and the data-availability wording (see `docs/journal_notes.md`).*
