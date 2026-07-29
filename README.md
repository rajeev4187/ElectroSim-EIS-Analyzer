# ElectroSim-EIS Analyzer

**A publication-ready Streamlit interface for Electrochemical Impedance
Spectroscopy (EIS) with private-model fitting.**

Maintained by **Rajeev Kumar** (<rkumar@nccu.edu>), North Carolina Central
University.

> This public repository contains the Streamlit web-demo only.
> Proprietary EIS fitting logic stays in a private "Working apps/EIS" project.

---

## What this repo does

The web app provides:

- **Nyquist plotting** from uploaded EIS files
- **Bode plotting** (|Z| and phase vs frequency)
- **Private-fit execution** via secure API call to your private EIS engine
- **Data preview** for quick validation before fitting

This repo intentionally excludes installer, desktop packaging, and private
analysis source.

---

## Public and private split

- **Public (this repo):** Streamlit UI in `release/web-demo/`
- **Private (your Working apps/EIS):** fitting engine and proprietary logic

The public app sends normalized EIS data to the private service endpoint:

- `POST /fit/eis`

Request payload shape:

```json
{
  "model": "Randles",
  "data": [
    {
      "frequency_hz": 1000.0,
      "z_real_ohm": 1.25,
      "z_imag_ohm": -0.62
    }
  ]
}
```

---

## Repository structure

```text
release/
  web-demo/
    ElectroSim-EIS.py
    requirements.txt
    .streamlit/
      config.toml
      secrets.toml.example
```

---

## Input data format

Required columns after normalization:

- `frequency_hz`
- `z_real_ohm`
- `z_imag_ohm`

Common aliases are normalized automatically (`freq`, `f`, `frequency(hz)`,
`zreal`, `zimag`, `Z'`, `Z''`, etc.).

Supported upload formats:

- CSV
- XLSX / XLS
- TXT (auto-detected delimiter)

---

## Running the web app locally

The web app lives in `release/web-demo/` and must be launched with
`streamlit run`:

```powershell
cd release\web-demo
py -3.13 -m pip install -r requirements.txt
py -3.13 -m streamlit run ElectroSim-EIS.py
```

Do not use plain `python ElectroSim-EIS.py`.

---

## Deploying publicly (low-cost)

1. Push this repository to GitHub (public).
2. Create an app on Streamlit Community Cloud.
3. Set main file path to `release/web-demo/ElectroSim-EIS.py`.
4. Add secrets in Streamlit Cloud app settings.
5. Deploy.

This is the lowest-cost hosting option for your public GUI.

---

## Streamlit secrets

Use `release/web-demo/.streamlit/secrets.toml.example` as template.

Set the values in Streamlit Cloud secrets (not in git):

```toml
PRIVATE_API_BASE_URL = "https://your-private-eis-service.example.com"
PRIVATE_API_TOKEN = "replace-with-strong-token"
REQUEST_TIMEOUT_SEC = 45
```

---

## Security notes

- Never commit private engine code to this repo.
- Never commit `.streamlit/secrets.toml`.
- Use short-lived tokens and rotate them periodically.
- Restrict private API access by CORS, firewall, or allowlist where possible.

---

## License

See `LICENSE` for usage terms.
