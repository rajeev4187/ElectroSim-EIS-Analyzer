"""ElectroSim-EIS Analyzer - Streamlit web-demo entry point.

This public app mirrors the full GUI workflow while keeping fitting and
advanced analysis logic in a private backend service.
"""

from __future__ import annotations

import io
import os
import sys
from dataclasses import dataclass
from typing import Any
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


def _verify_under_streamlit_run() -> None:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        sys.stderr.write(
            "\n[electrosim_app] Streamlit is not installed in this Python.\n"
            "  Install it first:    pip install streamlit\n"
            "  Then launch with:    streamlit run "
            + os.path.basename(__file__)
            + "\n\n"
        )
        sys.exit(1)

    if get_script_run_ctx() is None:
        sys.stderr.write(
            "\n[electrosim_app] This script must be launched with "
            "`streamlit run`, not plain `python`.\n\n"
            "  WRONG:  python "
            + os.path.basename(__file__)
            + "\n"
            "  RIGHT:  streamlit run "
            + os.path.basename(__file__)
            + "\n\n"
        )
        sys.exit(1)


_verify_under_streamlit_run()


@dataclass
class ApiConfig:
    base_url: Optional[str]
    token: Optional[str]
    timeout_sec: int


def _load_api_config() -> ApiConfig:
    base_url = st.secrets.get("PRIVATE_API_BASE_URL")
    token = st.secrets.get("PRIVATE_API_TOKEN")
    timeout_sec = int(st.secrets.get("REQUEST_TIMEOUT_SEC", 45))
    return ApiConfig(base_url=base_url, token=token, timeout_sec=timeout_sec)


def _api_ready(cfg: ApiConfig) -> bool:
    return bool(cfg.base_url and cfg.token)


def _request_private_api(
    endpoint: str,
    payload: dict[str, Any],
    cfg: ApiConfig,
) -> dict[str, Any]:
    if not _api_ready(cfg):
        raise RuntimeError(
            "Private API settings are missing in Streamlit secrets."
        )

    headers = {
        "Authorization": f"Bearer {cfg.token}",
        "Content-Type": "application/json",
    }
    url = f"{cfg.base_url.rstrip('/')}{endpoint}"
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=cfg.timeout_sec,
    )
    response.raise_for_status()
    return response.json()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "freq": "frequency_hz",
        "f": "frequency_hz",
        "frequency": "frequency_hz",
        "frequency(hz)": "frequency_hz",
        "zreal": "z_real_ohm",
        "z'": "z_real_ohm",
        "real": "z_real_ohm",
        "zimag": "z_imag_ohm",
        "z''": "z_imag_ohm",
        "imag": "z_imag_ohm",
        "eps": "epsilon_r",
        "epsilon": "epsilon_r",
        "dielectric": "epsilon_r",
        "voltage": "voltage_v",
        "v": "voltage_v",
        "potential": "voltage_v",
        "c": "capacitance_f",
        "capacitance": "capacitance_f",
        "capacitance(f)": "capacitance_f",
    }

    renamed = {}
    for col in df.columns:
        key = col.strip().lower().replace(" ", "")
        renamed[col] = mapping.get(key, col)

    return df.rename(columns=renamed)


def _parse_uploaded_file(uploaded: Any) -> pd.DataFrame:
    ext = uploaded.name.rsplit(".", 1)[-1].lower()
    file_bytes = uploaded.read()

    if ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif ext in {"xlsx", "xls"}:
        df = pd.read_excel(io.BytesIO(file_bytes))
    elif ext == "txt":
        df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine="python")
    else:
        raise ValueError("Unsupported file type. Use CSV, XLSX, XLS, or TXT.")

    return _normalize_columns(df)


def _validate_eis_columns(df: pd.DataFrame) -> tuple[bool, list[str]]:
    required = ["frequency_hz", "z_real_ohm", "z_imag_ohm"]
    missing = [col for col in required if col not in df.columns]
    return len(missing) == 0, missing


def _make_nyquist_plot(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["z_real_ohm"],
            y=-df["z_imag_ohm"],
            mode="markers+lines",
            marker={"size": 8},
            name="Nyquist",
        )
    )
    fig.update_layout(
        title="Nyquist Plot",
        xaxis_title="Z' (Ohm)",
        yaxis_title="-Z'' (Ohm)",
        template="plotly_white",
    )
    return fig


def _make_bode_plot(df: pd.DataFrame) -> go.Figure:
    freq = df["frequency_hz"].astype(float)
    z_real = df["z_real_ohm"].astype(float)
    z_imag = df["z_imag_ohm"].astype(float)
    z_mod = np.sqrt((z_real ** 2) + (z_imag ** 2))
    phase = np.degrees(np.arctan2(z_imag, z_real))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=freq,
            y=z_mod,
            mode="lines+markers",
            name="|Z|",
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=freq,
            y=phase,
            mode="lines+markers",
            name="Phase",
            yaxis="y2",
        )
    )

    fig.update_layout(
        title="Bode Plot",
        xaxis={"title": "Frequency (Hz)", "type": "log"},
        yaxis={"title": "|Z| (Ohm)", "type": "log"},
        yaxis2={
            "title": "Phase (deg)",
            "overlaying": "y",
            "side": "right",
        },
        legend={"x": 0.01, "y": 0.99},
        template="plotly_white",
    )
    return fig


def _run_private_fit(
    df: pd.DataFrame,
    model_name: str,
    cfg: ApiConfig,
) -> dict[str, Any]:
    payload = {
        "model": model_name,
        "data": df[
            ["frequency_hz", "z_real_ohm", "z_imag_ohm"]
        ].to_dict(orient="records"),
    }
    return _request_private_api("/fit/eis", payload, cfg)


def _make_mott_schottky_plot(df: pd.DataFrame) -> go.Figure:
    if "capacitance_f" not in df.columns or "voltage_v" not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            title="Mott-Schottky Plot",
            xaxis_title="Voltage (V)",
            yaxis_title="1/C^2 (F^-2)",
            annotations=[
                {
                    "text": "Upload data with voltage and capacitance columns",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                }
            ],
            template="plotly_white",
        )
        return fig

    c = pd.to_numeric(df["capacitance_f"], errors="coerce")
    v = pd.to_numeric(df["voltage_v"], errors="coerce")
    mask = c > 0
    c2_inv = 1.0 / (c[mask] ** 2)
    v_valid = v[mask]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=v_valid,
            y=c2_inv,
            mode="markers+lines",
            name="Mott-Schottky",
        )
    )
    fig.update_layout(
        title="Mott-Schottky Plot",
        xaxis_title="Voltage (V)",
        yaxis_title="1/C^2 (F^-2)",
        template="plotly_white",
    )
    return fig


def _render_private_result(title: str, endpoint: str, payload: dict[str, Any]):
    cfg = _load_api_config()
    if not _api_ready(cfg):
        st.warning(
            "Private backend is not configured. Add Streamlit secrets to "
            "enable this analysis."
        )
        return

    with st.spinner(f"Running {title} on private backend..."):
        try:
            result = _request_private_api(endpoint, payload, cfg)
            st.success(f"{title} completed.")
            st.json(result)
        except requests.HTTPError as exc:
            st.error(f"Private API returned an error: {exc}")
        except Exception as exc:  # pragma: no cover - UI guard
            st.error(f"{title} failed: {exc}")


def main() -> None:
    st.set_page_config(
        page_title="ElectroSim EIS Analyzer",
        page_icon="⚡",
        layout="wide",
    )

    st.title("ElectroSim EIS Analyzer")
    st.caption("Full GUI workflow with private backend compute")

    with st.sidebar:
        st.header("Input")
        uploaded = st.file_uploader(
            "Upload EIS data",
            type=["csv", "xlsx", "xls", "txt"],
        )
        model_name = st.selectbox(
            "Equivalent circuit model",
            ["Randles", "R(RQ)", "R(Q(RW))", "Custom API model"],
        )
        run_fit = st.button("Run Equivalent-Circuit Fit", type="primary")

    cfg = _load_api_config()
    if _api_ready(cfg):
        st.success("Private backend connected via secrets.")
    else:
        st.info(
            "Private backend not configured. Plotting works, but advanced "
            "analysis actions call private API and will remain disabled."
        )

    if not uploaded:
        st.info("Upload an EIS file to continue.")
        return

    try:
        df = _parse_uploaded_file(uploaded)
    except Exception as exc:
        st.error(f"Unable to parse file: {exc}")
        return

    ok, missing = _validate_eis_columns(df)
    if not ok:
        st.error(
            "Missing required columns after normalization: "
            + ", ".join(missing)
            + ". Expected frequency and complex impedance columns."
        )
        st.write("Detected columns:", list(df.columns))
        return

    tab_names = [
        "Data Files",
        "Data Plotting",
        "Nyquist",
        "Bode",
        "Mott-Schottky",
        "Equivalent Circuit",
        "Energy Levels",
    ]
    tabs = st.tabs(tab_names)
    (
        tab_data,
        tab_plot,
        tab_nyq,
        tab_bode,
        tab_ms,
        tab_fit,
        tab_energy,
    ) = tabs

    with tab_data:
        st.subheader("Loaded Dataset")
        st.dataframe(df.head(500), use_container_width=True)
        st.download_button(
            "Download normalized CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="normalized_eis_data.csv",
            mime="text/csv",
        )

    with tab_plot:
        st.subheader("Quick Data Plot")
        x_col = st.selectbox("X axis", list(df.columns), index=0)
        y_col = st.selectbox("Y axis", list(df.columns), index=1)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode="lines+markers",
                name=f"{y_col} vs {x_col}",
            )
        )
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col,
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_nyq:
        st.plotly_chart(_make_nyquist_plot(df), use_container_width=True)

    with tab_bode:
        st.plotly_chart(_make_bode_plot(df), use_container_width=True)

    with tab_ms:
        st.plotly_chart(_make_mott_schottky_plot(df), use_container_width=True)
        run_ms = st.button("Run Advanced Mott-Schottky Analysis")
        if run_ms:
            _render_private_result(
                title="Mott-Schottky analysis",
                endpoint="/analyze/mott-schottky",
                payload={"data": df.to_dict(orient="records")},
            )

    with tab_fit:
        st.subheader("Equivalent-Circuit Fitting")
        fit_mode = st.radio(
            "Optimization strategy",
            ["Auto", "Levenberg-Marquardt", "Differential Evolution"],
            horizontal=True,
        )
        include_kramers_kronig = st.checkbox(
            "Run Kramers-Kronig consistency check",
            value=True,
        )
        if run_fit:
            if not _api_ready(cfg):
                st.warning(
                    "Add private API secrets to run fitting. "
                    "Plots are available without backend."
                )
            else:
                with st.spinner("Calling private EIS fitting service..."):
                    try:
                        result = _run_private_fit(df, model_name, cfg)
                        st.success("Fit completed.")
                        st.subheader("Fit Output")
                        st.json(result)
                    except requests.HTTPError as exc:
                        st.error(f"Private API returned an error: {exc}")
                    except Exception as exc:  # pragma: no cover - UI guard
                        st.error(f"Fit failed: {exc}")

        if st.button("Run DRT Deconvolution"):
            _render_private_result(
                title="DRT deconvolution",
                endpoint="/analyze/drt",
                payload={
                    "model": model_name,
                    "fit_mode": fit_mode,
                    "include_kk": include_kramers_kronig,
                    "data": df.to_dict(orient="records"),
                },
            )

    with tab_energy:
        st.subheader("Energy-Level Diagram")
        ocp_v = st.number_input("Open-circuit potential (V)", value=0.0)
        band_gap_ev = st.number_input("Band gap (eV)", value=1.8)
        ref_scale = st.selectbox("Reference", ["Vacuum", "NHE", "Ag/AgCl"])
        if st.button("Generate Energy Diagram"):
            _render_private_result(
                title="Energy-level generation",
                endpoint="/analyze/energy-levels",
                payload={
                    "ocp_v": ocp_v,
                    "band_gap_ev": band_gap_ev,
                    "reference": ref_scale,
                    "data": df.to_dict(orient="records"),
                },
            )


if __name__ == "__main__":
    main()
