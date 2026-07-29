"""ElectroSim-EIS Analyzer - Streamlit web-demo entry point.

This public app contains only the GUI and plotting layer.
Private EIS fitting logic stays outside this repository and is called by API.
"""

from __future__ import annotations

import io
import os
import sys
from dataclasses import dataclass
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
    }

    renamed = {}
    for col in df.columns:
        key = col.strip().lower().replace(" ", "")
        renamed[col] = mapping.get(key, col)

    return df.rename(columns=renamed)


def _parse_uploaded_file(
    uploaded: st.runtime.uploaded_file_manager.UploadedFile,
) -> pd.DataFrame:
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


def _request_private_fit(
    df: pd.DataFrame,
    model_name: str,
    api_cfg: ApiConfig,
) -> dict:
    if not api_cfg.base_url or not api_cfg.token:
        raise RuntimeError(
            "Private API settings are missing in Streamlit secrets."
        )

    payload = {
        "model": model_name,
        "data": df[
            ["frequency_hz", "z_real_ohm", "z_imag_ohm"]
        ].to_dict(orient="records"),
    }
    headers = {
        "Authorization": f"Bearer {api_cfg.token}",
        "Content-Type": "application/json",
    }

    url = f"{api_cfg.base_url.rstrip('/')}/fit/eis"
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=api_cfg.timeout_sec,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    st.set_page_config(
        page_title="ElectroSim EIS Analyzer",
        page_icon="⚡",
        layout="wide",
    )

    st.title("ElectroSim EIS Analyzer")
    st.caption("Public Streamlit UI. Private EIS engine runs off-repo.")

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
        run_fit = st.button("Run Private Fit", type="primary")

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

    tab1, tab2, tab3 = st.tabs(["Nyquist", "Bode", "Data Preview"])
    with tab1:
        st.plotly_chart(_make_nyquist_plot(df), use_container_width=True)
    with tab2:
        st.plotly_chart(_make_bode_plot(df), use_container_width=True)
    with tab3:
        st.dataframe(df.head(300), use_container_width=True)

    if run_fit:
        api_cfg = _load_api_config()
        with st.spinner("Calling private EIS fitting service..."):
            try:
                result = _request_private_fit(df, model_name, api_cfg)
                st.success("Fit completed.")
                st.subheader("Fit Output")
                st.json(result)
            except requests.HTTPError as exc:
                st.error(f"Private API returned an error: {exc}")
            except Exception as exc:
                st.error(f"Fit failed: {exc}")


if __name__ == "__main__":
    main()
