# Output data dictionary

The pipeline writes `CD_similarity_results.xlsx` plus two machine-readable CSV files. Sheet names and column headers are in Chinese in the current release; this page gives the English mapping. The CSV files use English column names and are the recommended input for scripts.

## Files

| File | Content |
|---|---|
| `CD_similarity_results.xlsx` | Formatted workbook with all tables, matrices and native charts |
| `pairwise_metrics.csv` | One row per sample pair (288 rows for the published 8-workbook dataset) |
| `qc_spectra.csv` | One row per spectrum (72 rows for the published dataset) |
| `README_方法与结果.md` | Automatically generated Chinese report (per-workbook counts, top pairs, mirror groups) |

## Sheets

| Sheet | English name | Content |
|---|---|---|
| `00_说明` | Overview | Parameters, decision rules, limitations, self-test results |
| `01_QC` | Spectrum QC | Points, wavelength range, step, coverage, amplitude, noise, SNR, dominant band, spikes |
| `02_配对总表` | Pairwise metrics | Main table: scores, shifts, p/q values, band concordance, decision, confidence |
| `03_相似度矩阵` | Same-sense matrix | 9 × 9 matrices of \(S\) (derivative), one block per workbook |
| `04_镜像矩阵` | Mirror matrix | 9 × 9 matrices of \(M\) (derivative) |
| `05_位移矩阵` | Shift matrix | 9 × 9 matrices of \(\delta_S\) (nm); the matrix is antisymmetric because the shift is directional |
| `06_峰位表` | Cotton bands | Up to four bands per spectrum: position, sign, g-factor, prominence |
| `07_最佳配对` | Best matches | Top three same-sense and top three mirror partners for each spectrum |
| `08_图表` | Charts | Native Excel charts: overlay of the nine spectra per workbook, S–M scatter, representative pairs |
| `09_结论摘要` | Summary | Per-workbook class counts and threshold sensitivity |
| `10_谱图数据` | Chart source data | 1 nm interpolated spectra used by the charts |
| `11_SM数据` | S–M source data | \(S\) and \(M\) for the scatter plot |
| `12_代表谱对` | Representative pairs | Normalized spectra for the three representative pair charts |
| `13_镜像分组` | Mirror groups | Bipartite grouping of mirror-classified pairs per workbook |
| `14_最佳谱对` | Top pairs | Top 10 same-sense and top 10 mirror pairs across all workbooks |

## `02_配对总表` (pairwise table) columns

| Column | Meaning |
|---|---|
| `文件` | Workbook name |
| `样品A`, `样品B` | Sample labels \(X\)–\(Y\) |
| `A类型`, `B类型` | `pure_thiol2` (\(X\)–0), `pure_thiol1` (0–\(Y\)) or `mixture` |
| `对类型` | `endpoint` if either sample is an end member, otherwise `mixture` |
| `S_raw`, `S_hp`, `S_d` | Same-sense score \(S\) from the raw, high-pass and derivative representations |
| `δS_raw`, `δS_hp`, `δS_d` | Optimal same-sense shift \(\delta_S\) (nm) |
| `M_raw`, `M_hp`, `M_d` | Mirror score \(M\) |
| `δM_raw`, `δM_hp`, `δM_d` | Optimal mirror shift \(\delta_M\) (nm) |
| `r0_d` | Pearson correlation at zero shift (derivative) |
| `margin_d` | \(M-S\) (derivative) |
| `mirror_index` | \((M-S)/(M+S)\) |
| `pS`, `pM` | Empirical surrogate p-values |
| `qS`, `qM` | Benjamini–Hochberg adjusted p-values within the workbook |
| `带数` | Number of matched Cotton bands |
| `同号一致` | \(f_{\mathrm{same}}\), amplitude-weighted same-sign concordance |
| `镜像一致` | \(f_{\mathrm{mirror}}\), amplitude-weighted mirror-sign concordance |
| `带中位Δλ` | Median band-position difference (nm) |
| `SNR_A`, `SNR_B` | Signal-to-noise ratio of each spectrum |
| `判定` | Decision class (see below) |
| `置信度` | `高` (high), `中` (medium), `低` (low) |
| `备注` | Notes: boundary shift, low SNR, insufficient band evidence, metric conflict, end-member flag, non-significant |

The Excel table abbreviates the derivative columns as `S_d`, `M_d`, `δS_d` and `δM_d`; `pairwise_metrics.csv` uses the full names `S_deriv`, `M_deriv`, `dS_deriv` and `dM_deriv`.

## Decision classes

| Chinese label | English label |
|---|---|
| `同手性·高度一致` | Same-sense, high similarity |
| `同手性·位移型` | Same-sense, shifted (red/blue shift) |
| `镜像·手性翻转` | Mirror, chirality inversion |
| `镜像+位移` | Mirror plus shift |
| `弱/不可判定` | Weak / undetermined |
| `不相似` | Dissimilar |

## `01_QC` columns

| Column | Meaning |
|---|---|
| `文件`, `样品`, `类型` | Workbook, sample, end-member type |
| `点数`, `λmin`, `λmax`, `步长` | Number of points, wavelength range, median step |
| `300-500点数` | Points inside the analysis window |
| `覆盖280-520` | Whether the spectrum covers the padded shift grid |
| `幅度`, `噪声`, `SNR` | Amplitude (P98–P2), high-frequency noise, SNR |
| `主带λ`, `主带符号`, `主带g` | Dominant band position, sign and g-factor |
| `带数` | Number of detected Cotton bands |
| `尖峰点数` | Number of spike-like points flagged in the raw export |
