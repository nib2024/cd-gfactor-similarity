# Journal-specific notes: Nature Communications vs JACS

This note collects the practical differences and ready-to-paste statements. Replace every bracketed placeholder before submission.

## Common preparation

1. Replace `USERNAME`, `zenodo.XXXXXXX` and the author details in `CITATION.cff`, `README.md` and `docs/SI_methods.md`.
2. Create a public GitHub repository, push the code, tag the release (`git tag -a v1.0.0 -m "v1.0.0"`), create a GitHub Release, and archive the release on Zenodo. Use the DOI returned by Zenodo, not only the GitHub URL.
3. Choose a license. The repository ships with MIT; change the copyright line if your institution requires another license.
4. Do **not** commit raw experimental data, credentials, tokens or unpublished Source Data to the public repository. The repository contains only code, a synthetic demo dataset and tests.
5. Add the archived DOI to `README.md`, `CITATION.cff` and the SI.
6. If the paper has a Source Data file, make sure the column names match `docs/OUTPUTS.md`.

## Nature Communications

- Nature Communications requires separate **Code availability** and **Data availability** sections after the Methods. Use exactly these headings.
- The main Methods can give a one-sentence summary; the SI gives a concise description of the metrics and decision rules, and the repository contains the full implementation and parameter set.
- Cite the archived code with its Zenodo DOI in the Code availability section. A GitHub URL alone is not sufficient for the archived version.
- If figures are generated from the pairwise table or the matrices, deposit the underlying numerical values as Source Data and describe the mapping in the Source Data legend.
- Suggested main-text Code availability wording:

> **Code availability.** The analysis code used in this study is available at https://github.com/USERNAME/cd-gfactor-similarity (version 1.0.0) and is archived at https://doi.org/10.5281/zenodo.XXXXXXX. The repository contains the complete pipeline, a synthetic demo dataset in both export layouts, and unit tests.

- Suggested Data availability wording:

> **Data availability.** The CD g-factor data that support the findings of this study are provided as Source Data with this paper. The synthetic demo dataset used to test the code is included in the code repository. Raw spectra are available from the corresponding author upon reasonable request.

## JACS

- JACS places the detailed method in the Supporting Information. Use a section titled **Data Analysis** (or **Computational Methods**) and include `docs/SI_methods.md` there.
- Add a short **Code Availability** paragraph at the end of the SI (after the Data Analysis section or in the final "Additional information" block).
- JACS increasingly expects a **Data Availability Statement** in the main text or at the end of the manuscript; check the current author guidelines at submission. When in doubt, include both a main-text Data availability statement and the SI Code Availability paragraph.
- The archived Zenodo DOI can be cited as a reference in the SI; in the main text, cite the repository/DOI in the Code Availability paragraph.
- Suggested SI Code Availability wording:

> **Code Availability.** The complete analysis pipeline, including data parsing, spectral preprocessing, shift-search similarity and mirror metrics, Cotton-band matching, surrogate-based significance testing, and generation of all tables, is available at https://github.com/USERNAME/cd-gfactor-similarity (version 1.0.0) and archived at https://doi.org/10.5281/zenodo.XXXXXXX. The repository includes a synthetic demo dataset in both export layouts, unit tests, and documentation. Raw experimental data are available from the corresponding author upon reasonable request.

## Suggested short sentence for the main text (either journal)

> The similarity, mirror-similarity and wavelength-shift analysis was performed with a custom Python pipeline (https://github.com/USERNAME/cd-gfactor-similarity; archived at https://doi.org/10.5281/zenodo.XXXXXXX), which is described in detail in the Supplementary Methods.

## What the repository contains

| Path | Content |
|---|---|
| `cd_compare.py` | Main pipeline: parsing, metrics, decisions, Excel/CSV output |
| `cd_metrics.py` | Numerical core: SG filters, correlations, shift search, surrogates, band matching, FDR, classification |
| `examples/make_demo_data.py` | Generates a synthetic demo dataset in both export layouts |
| `examples/demo_data/` | Demo workbooks (synthetic, not experimental data) |
| `tests/` | Unit and end-to-end tests (`python -m unittest discover -s tests -v`) |
| `docs/SI_methods.md` | Concise SI methods text (this document's companion) |
| `docs/OUTPUTS.md` | Data dictionary for the output tables |
| `docs/journal_notes.md` | This file |

## Reproducibility checklist

- [ ] Python 3.12.14, NumPy 2.3.5, openpyxl 3.1.5 (or the versions in `requirements.txt`)
- [ ] Random seed 20261114
- [ ] 2000 phase-randomized surrogates
- [ ] Per-workbook Benjamini–Hochberg FDR
- [ ] Raw data not committed; demo data and tests committed
- [ ] `v1.0.0` tag and Zenodo DOI
- [ ] DOI and repository URL inserted in the SI and README
- [ ] License and `CITATION.cff` completed

## Converting the SI to Word

The SI is written in Markdown with LaTeX equations. If Pandoc is available, convert it to a Word document with native equations:

```bash
pandoc docs/SI_methods.md -o SI_methods.docx
```

Open the result in Word, apply the journal's SI template (font, spacing, page numbers), and replace the placeholders. The SI is a short text with no tables.
