# ElectroSim-EIS Analyzer

**A Streamlit app for Electrochemical Impedance Spectroscopy (EIS) analysis.**

Maintained by **Rajeev Kumar** (<rkumar@nccu.edu>), North Carolina Central
University.

Open the live app: [ElectroSim-EIS Analyzer on Streamlit](https://electrosim-eis-analyzer.streamlit.app/)

---

## What you can do

This app is organized around the EIS workflow used in the private suite:

- **Nyquist**: upload impedance spectra, map real/imaginary columns, overlay
  plots, read approximate Rs/Rct landmarks, run a circuit fit, and check an
  admittance (Y = 1/Z) view plus inductive-loop/open-arc diagnostics.
- **Bode**: upload magnitude and/or phase data, overlay plots, and inspect the
  characteristic frequency.
- **Mott-Schottky**: upload summary curves or raw spectra, plot 1/C² vs
  potential, and extract flat-band/carrier-density information.
- **Battery**: fit a finite-length (bounded) Warburg circuit, get D_Li⁺ from
  the Z′ vs ω⁻¹ᐟ² line, and break down degradation across cycles by process
  (SEI, charge transfer, diffusion).
- **Solid-State Electrolyte**: decompose a temperature series into
  bulk/grain-boundary/electrode resistances, fit activation energy per
  process, and track interfacial degradation over time.
- **Band diagram**: turn fitted Mott-Schottky results into a simple energy
  summary for multiple materials.
- **Tutorials**: read the key equations and the short workflow explanation.

Both battery-facing tabs also offer **DRT** (Distribution of Relaxation
Times), a model-free deconvolution that counts and sizes processes without
committing to a circuit topology.

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

Common column names are auto-detected where possible, including `freq`, `f`,
`frequency(hz)`, `zreal`, `zimag`, `Z'`, and `Z''`.

Supported uploads:

- CSV
- XLSX / XLS
- TXT and similar delimited text files

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

If this tool contributes to your research, please cite it as:

> Kumar, R. (2026). *ElectroSim-EIS Analyzer* [Computer software].
> North Carolina Central University.
> <https://github.com/rajeev4187/ElectroSim-EIS-Analyzer>

BibTeX:

```bibtex
@software{kumar_electrosim_eis_analyzer,
  author  = {Kumar, Rajeev},
  title   = {ElectroSim-EIS Analyzer},
  year    = {2026},
  url     = {https://github.com/rajeev4187/ElectroSim-EIS-Analyzer}
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
