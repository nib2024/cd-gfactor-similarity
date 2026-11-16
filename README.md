# cd-gfactor-similarity

Reference implementation for pairwise **similarity** and **mirror-image similarity** analysis of circular dichroism (CD) **g-factor** spectra, with a rigid wavelength-shift search (±20 nm), Cotton-band matching, phase-randomized surrogate significance testing and false-discovery-rate control.

The code accompanies the manuscript on thiol-stabilised chiral nanoclusters. It compares the nine spectra inside one workbook, not across workbooks, and reports for every pair whether the two spectra are the same-sense, mirror-image, shifted, weak or dissimilar.

## Key features

- Parses both export layouts used by the JASCO software (interleaved wavelength/g-factor pairs, or one shared wavelength column).
- Ignores instrument-metadata rows automatically.
- Computes Pearson, cosine/SAM and NRMSE on raw, high-pass and first-derivative representations.
- Searches a global rigid shift from −20 to +20 nm in 0.5 nm steps without truncating the 300–500 nm comparison window.
- Separates the same-sense score \(S\) from the mirror score \(M\) and reports the optimal shifts for both.
- Matches Cotton bands by position and sign as an independent check.
- Estimates significance with 2000 phase-randomized surrogates and Benjamini–Hochberg FDR within each workbook.
- Writes an Excel workbook with formatted tables, 9 × 9 matrices and native charts, plus tidy CSV files.

## Repository layout

```
cd-gfactor-similarity/
├── cd_compare.py              # main pipeline
├── cd_metrics.py              # numerical core
├── examples/
│   ├── make_demo_data.py      # synthetic demo data generator
│   └── demo_data/             # two demo workbooks (synthetic, not experimental)
├── tests/
│   ├── test_io.py
│   ├── test_metrics.py
│   └── test_pipeline.py
├── docs/
│   ├── SI_methods.md          # full SI methods text
│   ├── OUTPUTS.md             # data dictionary
│   └── journal_notes.md       # Nature Communications / JACS notes
├── requirements.txt
├── LICENSE
└── CITATION.cff
```

## Requirements

- Python ≥ 3.9 (tested with 3.12.14)
- NumPy (tested with 2.3.5)
- openpyxl (tested with 3.1.5)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

No SciPy, scikit-learn or matplotlib is required; Savitzky–Golay filtering, peak detection, phase randomization, the Benjamini–Hochberg procedure and all metrics are implemented in NumPy.

## Quick start on the synthetic demo

```bash
python examples/make_demo_data.py
python cd_compare.py --input examples/demo_data --out demo_out --surrogates 200
```

`demo_out/CD_similarity_results.xlsx` contains the full set of tables and charts; `demo_out/pairwise_metrics.csv` is the machine-readable pairwise table. Increase `--surrogates` to 2000 for the settings used in the manuscript.

## Running on experimental data

Expected input: one `.xlsx` workbook per condition, each containing nine samples named `16-0, 14-2, 12-4, 10-6, 8-8, 6-10, 4-12, 2-14, 0-16`. Two layouts are supported:

```
# Layout A: interleaved pairs
Sample: 16-0 |            | Sample: 14-2 |            | ...
wavelength   | g-factor   | wavelength   | g-factor   | ...

# Layout B: shared wavelength column
              | Sample: 16-0 | Sample: 14-2 | ...
wavelength    | g-factor     | g-factor     | ...
```

Only rows in which both wavelength and g-factor are numeric are used, so trailing instrument metadata is ignored. Each workbook is analysed independently:

```bash
python cd_compare.py \
  --input  "/path/to/raw data" \
  --out    "out" \
  --surrogates 2000 \
  --seed 20261114
```

The default parameters are those used in the manuscript. The analysis window is 300–500 nm; spectra are resampled to 280–520 nm at 0.5 nm so that ±20 nm shifts require no extrapolation.

## Outputs

| File | Content |
|---|---|
| `out/CD_similarity_results.xlsx` | 15 sheets: QC, 288-row pairwise table, 9 × 9 similarity/mirror/shift matrices, Cotton bands, best matches, charts, summary, mirror groups, top pairs |
| `out/pairwise_metrics.csv` | One row per pair (English column names) |
| `out/qc_spectra.csv` | One row per spectrum |
| `out/README_方法与结果.md` | Auto-generated Chinese report |

The Excel sheet names and some headers are in Chinese in this release; see [`docs/OUTPUTS.md`](docs/OUTPUTS.md) for the English mapping. The CSV files are the recommended input for downstream scripts.

## Method summary

For a pair of spectra \(A\) and \(B\), the pipeline computes the Pearson correlation \(r_{AB}(\delta)\) between \(A(\lambda)\) and \(B(\lambda+\delta)\) on the 300–500 nm window for \(\delta\in[-20,20]\) nm. The same-sense score is \(S=\max_\delta r_{AB}(\delta)\). Because a mirror-image CD spectrum has \(g\to-g\), the mirror score is \(M=\max_\delta[-r_{AB}(\delta)]=-\min_\delta r_{AB}(\delta)\). The optimal shifts, the margin \(M-S\), Cotton-band sign concordance and phase-randomized surrogate p-values are combined into the decision classes *same-sense high similarity*, *same-sense shifted*, *mirror*, *mirror plus shift*, *weak/undetermined* and *dissimilar*. The complete description, equations and parameter table are in [`docs/SI_methods.md`](docs/SI_methods.md).

## Reproducibility

- Random seed: `20261114`
- Surrogates: 2000
- FDR: Benjamini–Hochberg within each workbook (36 tests), q < 0.05
- Thresholds: \(S\) or \(M\ge0.70\); margin \(\ge0.20\); shift \(\ge3\) nm; SNR \(\ge20\); band mirror concordance \(\ge0.60\)
- Runtime: about 90 s for 288 pairs with 2000 surrogates on a laptop

## Tests

```bash
python -m unittest discover -s tests -v
```

The suite covers both workbook layouts, self-correlation, mirror recovery, synthetic shift recovery, FDR monotonicity, the decision thresholds and an end-to-end run on the demo data.

## Citation

If you use this code, please cite the manuscript and the archived release. Update `CITATION.cff` with the author details and the Zenodo DOI before archival.

## License

MIT. See [`LICENSE`](LICENSE).

## Code and data availability

The code is released at `https://github.com/USERNAME/cd-gfactor-similarity` and archived at `https://doi.org/10.5281/zenodo.XXXXXXX`. The repository contains only code, a synthetic demo dataset and tests; raw experimental data are available from the corresponding author upon reasonable request.

## Contact

Please open an issue on GitHub for questions about the code, or contact the corresponding author of the manuscript for questions about the data.
