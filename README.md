# ElectroSim-EIS Analyzer

**A Streamlit app for Electrochemical Impedance Spectroscopy (EIS) analysis.**

Maintained by **Rajeev Kumar** (<rkumar@nccu.edu>), North Carolina Central
University.

Open the live app: [ElectroSim-EIS Analyzer on Streamlit](https://electrosim-eis-analyzer.streamlit.app/)

---

## What you can do

This app is organized around the EIS workflow used in the private suite:

- **Nyquist**: upload impedance spectra, map real/imaginary columns, overlay
  plots, read approximate Rs/Rct landmarks, and run a circuit fit.
- **Bode**: upload magnitude and/or phase data, overlay plots, and inspect the
  characteristic frequency.
- **Mott-Schottky**: upload summary curves or raw spectra, plot 1/C² vs
  potential, and extract flat-band/carrier-density information.
- **Band diagram**: turn fitted Mott-Schottky results into a simple energy
  summary for multiple materials.
- **Tutorials**: read the key equations and the short workflow explanation.

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

---

## License

See `LICENSE` for usage terms.
