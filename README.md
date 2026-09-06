<div align="center">

# 🔌 ElectroSim-EIS Analyzer

**A Streamlit app for Electrochemical Impedance Spectroscopy (EIS) analysis.**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://electrosim-eis-analyzer.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](release/web-demo/requirements.txt)
[![Circuit models](https://img.shields.io/badge/circuit%20models-25-informational)](#circuit-models--fitting)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.22447886-blue.svg)](https://doi.org/10.5281/zenodo.22447886)

Maintained by **Rajeev Kumar** (<rkumar@nccu.edu>), North Carolina Central
University

**[🚀 Open the live app](https://electrosim-eis-analyzer.streamlit.app/)** ·
[Report an issue](https://github.com/rajeev4187/ElectroSim-EIS-Analyzer/issues) ·
[Cite this tool](#how-to-cite)

<!-- TODO: swap in a real screenshot/GIF of the app once one is captured -->
<img src="https://placehold.co/960x520/0f172a/ffffff?text=ElectroSim-EIS+Analyzer" alt="App screenshot placeholder" width="100%">

</div>

---

## Contents

[What you can do](#what-you-can-do) ·
[Circuit models & fitting](#circuit-models--fitting) ·
[Workflow](#workflow) ·
[Input at a glance](#input-at-a-glance) ·
[Tutorials summary](#tutorials-summary) ·
[How to cite](#how-to-cite)

---

## What you can do

This app is organized around the EIS workflow used in the private suite:

**Reads instrument files directly.** Besides CSV/Excel/TXT, every uploader
also takes raw **BioLogic EC-Lab `.mpr`/`.mpt`** and **Pine Research
AfterMath `.paax`** exports, frequency included, with a picker when one file
bundles several experiments.

- **Nyquist**: upload impedance spectra, map real/imaginary columns, overlay
  plots, read approximate Rs/Rct landmarks, run a circuit fit, and check an
  admittance (Y = 1/Z) view plus inductive-loop/open-arc diagnostics.
- **Bode**: upload magnitude and/or phase data, overlay plots, and inspect the
  characteristic frequency.
- **Mott-Schottky**: upload summary curves or raw spectra, plot 1/C² vs
  potential, and extract flat-band/carrier-density information.
- **Battery**: fit a finite-length (bounded) Warburg circuit, get D_Li⁺ from
  the Z′ vs ω⁻¹ᐟ² line, break down degradation across cycles by process (SEI,
  charge transfer, diffusion), and read electrode tortuosity/MacMullin number
  from a symmetric blocking-electrolyte cell.
- **Solid-State Electrolyte**: decompose a temperature series into
  bulk/grain-boundary/electrode resistances, fit activation energy per
  process, and track interfacial degradation over time.
- **Corrosion**: fit the Rs + (Rct ∥ CPE) corrosion-cell circuit and get
  corrosion current density/rate via Stern–Geary and ASTM G102, or upload a
  time series for a protective coating to track pore resistance and read
  % water uptake (Brasher–Kingsbury) as it degrades.
- **Sensing**: upload one spectrum per analyte concentration (plus a blank)
  to build a calibration curve and get limit of detection/quantification
  (LOD/LOQ), either from a fixed-frequency reading or a batch circuit fit.
- **Band diagram**: turn fitted Mott-Schottky results into a simple energy
  summary for multiple materials.
- **Tutorials**: read the key equations and the short workflow explanation.

Nyquist, Battery, Solid-State Electrolyte, and Corrosion all detect and
explain the two ways a Nyquist trace curls inward — an inductive loop and an
arc that never closes. Battery and Solid-State Electrolyte also offer
**DRT** (Distribution of Relaxation Times), a model-free deconvolution that
counts and sizes processes without committing to a circuit topology.

---

## Circuit models & fitting

Every analyzer shares one circuit-fitting engine: complex nonlinear
least-squares with multi-start restarts (to avoid a fit landing in a local
minimum), an RMS relative-residual (%) fit-quality score alongside the
Kramers–Kronig check, and a batch-fit mode that tracks parameters across a
time or temperature series. A circuit builder lets you pick from **25 built-in
equivalent circuits**, from the basic Rs / Randles / two-time-constant family
up through specialized literature models for particular systems:

- Inductive loops (high- and low-frequency), and finite-length (bounded)
  Warburg diffusion for batteries
- A porous-electrode transmission line for tortuosity, and a 3-time-constant
  bulk/grain-boundary/electrode model for solid electrolytes
- Graphite-SEI and coated-metal two-arc models for degradation and corrosion
- A Gerischer element and finite-length Gerischer for SOFC/fuel-cell
  cathodes, and a mixed ionic-electronic conductor (MIEC) transmission line
- Cole–Cole (bioimpedance), dual-Randles (PEM electrolyzers), and
  diffusion-recombination transmission lines for perovskite/DSSC solar cells
- Parallel-diffusion Warburg and Maxwell–Wagner relaxation for composite and
  solid polymer electrolytes

---

## Workflow

1. Start in the analyzer that matches your file type.
2. Upload one or more files.
3. Confirm the auto-mapped columns.
4. Review the overlay plot and the quick-read values.
5. Run the fit or interpretation step if needed.
6. Use the Tutorials tab for the equations behind each result.

The common pattern is the same in every analyzer: upload first, map columns,
inspect the plot, then interpret the output.

---

## Input at a glance

- **Nyquist**: `frequency_hz`, `z_real_ohm`, `z_imag_ohm`
- **Bode**: frequency with `|Z|` and/or phase
- **Mott-Schottky**: potential with either `C` or `1/C²`
- **Corrosion / Sensing**: same as Nyquist — Z′/Z″ vs frequency

Common column names are auto-detected where possible, including `freq`, `f`,
`frequency(hz)`, `zreal`, `zimag`, `Z'`, and `Z''`.

Supported uploads:

- CSV
- XLSX / XLS
- TXT and similar delimited text files
- Raw instrument exports, parsed directly (frequency included): **BioLogic
  EC-Lab** `.mpr` / `.mpt` and **Pine Research AfterMath** `.paax`

---

## Tutorials summary

The Tutorials tab briefly defines the core EIS relationships used by the app:

- complex impedance and phase
- resistor, capacitor, CPE, and Warburg elements
- the Randles circuit
- area-normalized quantities such as Rs·A, Cdl/A, and j₀
- the Mott-Schottky equation for flat-band and carrier-density estimates
- finite-length (bounded) Warburg diffusion and D_Li⁺ from the Z′ vs ω⁻¹ᐟ²
  line
- the Arrhenius relation for activation energy from a temperature series
- DRT (Distribution of Relaxation Times) as a model-free alternative to
  circuit fitting

---

## How to cite

If this tool contributes to your research, please cite the archived release
on Zenodo:

> Kumar, R. (2026). *ElectroSim-EIS Analyzer* (V2.0) [Computer software].
> North Carolina Central University. Zenodo.
> <https://doi.org/10.5281/zenodo.22447886>

BibTeX:

```bibtex
@software{kumar_electrosim_eis_analyzer,
  author  = {Kumar, Rajeev},
  title   = {ElectroSim-EIS Analyzer},
  version = {V2.0},
  year    = {2026},
  publisher = {Zenodo},
  doi     = {10.5281/zenodo.22447886},
  url     = {https://doi.org/10.5281/zenodo.22447886}
}
```

A machine-readable [`CITATION.cff`](CITATION.cff) is also included, which
GitHub uses to power the "Cite this repository" button on the repo page.

## Acknowledgments

Development of this app was assisted by AI coding tools — **Claude**
(Anthropic) and **GitHub Copilot** — used to help write and modify parts of
the codebase.

## License

See `LICENSE` for usage terms.
