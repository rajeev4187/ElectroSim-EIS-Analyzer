"""ElectroSim-EIS Analyzer - Streamlit web-demo entry point.

The public app mirrors the private suite flow:
sidebar settings plus analyzer tabs for Nyquist, Bode,
Mott-Schottky, Band diagram, and Tutorials.
"""

from __future__ import annotations

import io
import os
import sys
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st


SUPPORTED_EXTENSIONS = ["csv", "xlsx", "xls", "txt", "dat", "ascii"]
COLORWAY = [
    "#377eb8",
    "#e41a1c",
    "#4daf4a",
    "#984ea3",
    "#ff7f00",
    "#a65628",
    "#f781bf",
]
UNIT_MAP = {
    "Ohm (Ω)": 1.0,
    "milli-Ohm (mΩ)": 1e-3,
    "kilo-Ohm (kΩ)": 1e3,
    "Ohm·cm² (Ω·cm²)": "area",
}
FREQ_UNITS = {"GHz": 1e9, "MHz": 1e6, "kHz": 1e3, "Hz": 1.0, "mHz": 1e-3}


@dataclass
class ApiConfig:
    base_url: Optional[str]
    token: Optional[str]
    timeout_sec: int = 45


def _verify_under_streamlit_run() -> None:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        sys.stderr.write(
            "\n[electrosim_app] Streamlit is not installed.\n"
            "Install it with: pip install streamlit\n"
            "Then run: streamlit run "
            + os.path.basename(__file__)
            + "\n\n"
        )
        sys.exit(1)

    if get_script_run_ctx() is None:
        sys.stderr.write(
            "\n[electrosim_app] Use `streamlit run`, not plain `python`.\n\n"
            "WRONG: python "
            + os.path.basename(__file__)
            + "\n"
            "RIGHT: streamlit run "
            + os.path.basename(__file__)
            + "\n\n"
        )
        sys.exit(1)


_verify_under_streamlit_run()


def _load_api_config() -> ApiConfig:
    try:
        return ApiConfig(
            base_url=st.secrets.get("PRIVATE_API_BASE_URL"),
            token=st.secrets.get("PRIVATE_API_TOKEN"),
            timeout_sec=int(st.secrets.get("REQUEST_TIMEOUT_SEC", 45)),
        )
    except Exception:
        return ApiConfig(base_url=None, token=None, timeout_sec=45)


def _api_ready(cfg: ApiConfig) -> bool:
    return bool(cfg.base_url and cfg.token)


def _request_private_api(
    endpoint: str,
    payload: dict[str, Any],
    cfg: ApiConfig,
) -> dict[str, Any]:
    if not _api_ready(cfg):
        raise RuntimeError("Private API settings are missing.")

    headers = {
        "Authorization": f"Bearer {cfg.token}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        f"{cfg.base_url.rstrip('/')}{endpoint}",
        json=payload,
        headers=headers,
        timeout=cfg.timeout_sec,
    )
    response.raise_for_status()
    return response.json()


def _num(series):
    return pd.to_numeric(series, errors="coerce")


def _arrow_safe(df: pd.DataFrame | None):
    if df is None or getattr(df, "empty", False):
        return df
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].astype(str)
    return out


def _read_eis_file(uploaded):
    name = uploaded.name.lower()
    raw = uploaded.getvalue()
    if name.endswith((".xlsx", ".xls")):
        try:
            return pd.read_excel(io.BytesIO(raw))
        except Exception:
            return None

    for sep in (",", None, ";", "\t"):
        try:
            df = pd.read_csv(io.BytesIO(raw), sep=sep, engine="python")
            if df.shape[1] >= 2:
                df.columns = [str(c).strip() for c in df.columns]
                return df
        except Exception:
            continue
    return None


def _guess_unit_label(name: str) -> str:
    low = (name or "").lower()
    if "mohm" in low or "mΩ" in low:
        return "milli-Ohm (mΩ)"
    if "kohm" in low or "kΩ" in low:
        return "kilo-Ohm (kΩ)"
    if "cm²" in low or "cm2" in low:
        return "Ohm·cm² (Ω·cm²)"
    return "Ohm (Ω)"


def _role_idx(cols: list[str], role: Optional[str]) -> int:
    if role in cols:
        return cols.index(role) + 1
    return 0


def _detect_impedance_columns(df: pd.DataFrame) -> dict[str, Optional[str]]:
    cols = [str(c) for c in df.columns]
    low = {c.lower(): c for c in cols}
    roles: dict[str, Optional[str] | bool] = {
        "zreal": None,
        "zimag": None,
        "freq": None,
        "zimag_negated": False,
    }
    for key, col in low.items():
        if roles["zreal"] is None and any(
            t in key for t in ["zreal", "real", "zr", "z'"]
        ):
            roles["zreal"] = col
        if roles["zimag"] is None and any(
            t in key for t in ["zimag", "imag", "zi", "z''"]
        ):
            roles["zimag"] = col
        if roles["freq"] is None and any(
            t in key for t in ["freq", "frequency", "hz"]
        ):
            roles["freq"] = col
        if "-imaginary" in key or "-zi" in key:
            roles["zimag_negated"] = True
    return roles  # type: ignore[return-value]


def _detect_ms_columns(df: pd.DataFrame) -> dict[str, Optional[str]]:
    cols = [str(c) for c in df.columns]
    low = {c.lower(): c for c in cols}
    roles: dict[str, Optional[str] | bool] = {
        "potential": None,
        "value": None,
        "value_is_inv_sq": False,
    }
    for key, col in low.items():
        if roles["potential"] is None and any(
            t in key for t in ["potential", "voltage", "e (v)", "e_v"]
        ):
            roles["potential"] = col
        if roles["value"] is None and any(
            t in key for t in ["capacitance", "1/c", "c^-2", "inv"]
        ):
            roles["value"] = col
            roles["value_is_inv_sq"] = True
    return roles  # type: ignore[return-value]


def _to_ohm(series, unit_label: str, area_cm2: float):
    raw = _num(series)
    unit = UNIT_MAP.get(unit_label, 1.0)
    if unit == "area":
        return raw / max(area_cm2, 1e-12)
    return raw * float(unit)


def _nice_axis(vmax, vmin=0.0, target=5):
    import math

    if not (np.isfinite(vmax) and np.isfinite(vmin)) or vmax <= vmin:
        return 0.0, 1.0, 0.5
    raw = (vmax - vmin) / max(1, target - 1)
    mag = 10.0 ** math.floor(math.log10(raw))
    for mult in (1, 2, 2.5, 5, 10):
        if mult * mag >= raw:
            step = mult * mag
            break
    else:
        step = 10 * mag
    lo = math.floor(vmin / step) * step
    hi = math.ceil(vmax / step) * step
    return lo, hi, step


def _square_nyquist(fig, xs, ys, target=5):
    ax = np.asarray(xs, float)
    ay = np.asarray(ys, float)
    ax = ax[np.isfinite(ax)]
    ay = ay[np.isfinite(ay)]
    if not len(ax) or not len(ay):
        return fig
    dmax = max(ax.max(), ay.max())
    dmin = min(ax.min(), ay.min())
    lo, hi, step = _nice_axis(dmax, min(dmin, 0.0), target=target)
    if lo < 0 and dmin > -0.1 * hi:
        lo = 0.0
    fig.update_xaxes(range=[lo, hi], dtick=step, constrain="domain")
    fig.update_yaxes(
        range=[lo, hi],
        dtick=step,
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
    )
    return fig


def _plot_downloads(fig, stem, data_df=None):
    cols = st.columns(3 if data_df is not None else 2)
    cols[0].download_button(
        "⬇️ Chart (interactive HTML)",
        data=fig.to_html(include_plotlyjs="cdn").encode("utf-8"),
        file_name=f"{stem}.html",
        mime="text/html",
        key=f"dl_html_{stem}",
    )
    if data_df is not None:
        cols[1].download_button(
            "⬇️ Data (CSV)",
            data=data_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{stem}.csv",
            mime="text/csv",
            key=f"dl_csv_{stem}",
        )


def _journal_style(fig):
    tick = int(st.session_state.get("fig_tick", 28))
    title = int(st.session_state.get("fig_title", 36))
    fam = st.session_state.get("fig_font", "Arial")
    m = fig.layout.margin
    fig.update_layout(
        font=dict(family=fam, size=tick, color="black"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(
            l=m.l if m.l is not None else 110,
            r=m.r if m.r is not None else 90,
            t=m.t if m.t is not None else 60,
            b=m.b if m.b is not None else 100,
        ),
        legend=dict(font=dict(family=fam, size=max(11, int(tick * 0.6)))),
    )
    axis = dict(
        showline=True,
        linewidth=2,
        linecolor="black",
        mirror=True,
        ticks="outside",
        tickwidth=2,
        ticklen=7,
        tickcolor="black",
        showgrid=False,
        zeroline=False,
        tickfont=dict(family=fam, size=tick, color="black"),
        title_font=dict(family=fam, size=title, color="black"),
    )
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig


def _pchart(fig, **kwargs):
    _journal_style(fig)
    kwargs.setdefault("width", "stretch")
    return st.plotly_chart(fig, **kwargs)


def _make_nyquist_plot(datasets, area_cm2: float):
    fig = go.Figure()
    rows = []
    xs_all, ys_all = [], []
    for idx, ds in enumerate(datasets):
        zr = _to_ohm(ds["df"][ds["zre"]], ds["unit"], area_cm2)
        zi = _to_ohm(ds["df"][ds["zim"]], ds["unit"], area_cm2)
        zpp_true = -zi if ds["neg"] else zi
        neg_zpp = -zpp_true
        fig.add_trace(
            go.Scatter(
                x=zr,
                y=neg_zpp,
                mode="lines+markers",
                name=ds["name"],
                line=dict(color=COLORWAY[idx % len(COLORWAY)], width=2),
                marker=dict(size=6),
            )
        )
        rows.append(
            pd.DataFrame(
                {
                    "Z_real_Ohm": zr,
                    "neg_Z_imag_Ohm": neg_zpp,
                    "dataset": ds["name"],
                }
            )
        )
        xs_all.append(np.asarray(zr, float))
        ys_all.append(np.asarray(neg_zpp, float))
    fig.update_layout(
        xaxis_title="Z′ (Ω)",
        yaxis_title="−Z″ (Ω)",
        width=640,
        height=620,
        margin=dict(l=110, r=40, t=40, b=90),
    )
    _square_nyquist(
        fig,
        np.concatenate(xs_all) if xs_all else [0, 1],
        np.concatenate(ys_all) if ys_all else [0, 1],
    )
    return fig, (pd.concat(rows, ignore_index=True) if rows else None)


def _make_bode_plot(datasets, area_cm2: float):
    figb = make_subplots(specs=[[{"secondary_y": True}]])
    bode_rows = []
    ph_all = []
    f_char = None

    mag_sets = [d for d in datasets if d["zmod"] != "(none)"]
    ph_sets = [d for d in datasets if d["phase"] != "(none)"]

    for idx, ds in enumerate(mag_sets):
        f = _num(ds["df"][ds["freq"]])
        zm = _to_ohm(ds["df"][ds["zmod"]], ds["unit"], area_cm2)
        name = "|Z|" if len(datasets) == 1 else f"|Z| — {ds['name']}"
        figb.add_trace(
            go.Scatter(
                x=f,
                y=zm,
                mode="lines+markers",
                name=name,
                line=dict(color=COLORWAY[idx % len(COLORWAY)], width=2),
                marker=dict(size=5),
            ),
            secondary_y=False,
        )
        bode_rows.append(
            pd.DataFrame(
                {
                    "frequency_Hz": f,
                    "quantity": f"|Z|_Ohm ({ds['name']})",
                    "value": zm,
                }
            )
        )

    for idx, ds in enumerate(ph_sets):
        f = _num(ds["df"][ds["freq"]])
        ph = _num(ds["df"][ds["phase"]])
        if ds["phase_unit"] == "radians":
            ph = np.degrees(ph)
        ph_all.append(np.asarray(ph, float))
        name = "phase" if len(datasets) == 1 else f"phase — {ds['name']}"
        figb.add_trace(
            go.Scatter(
                x=f,
                y=ph,
                mode="lines+markers",
                name=name,
                line=dict(
                    color=COLORWAY[(idx + 4) % len(COLORWAY)],
                    width=2,
                    dash="dot",
                ),
                marker=dict(size=5, symbol="diamond"),
            ),
            secondary_y=True,
        )
        bode_rows.append(
            pd.DataFrame(
                {
                    "frequency_Hz": f,
                    "quantity": f"phase_deg ({ds['name']})",
                    "value": ph,
                }
            )
        )
        pp = pd.DataFrame({"f": f, "ph": ph}).dropna()
        if f_char is None and len(pp):
            f_char = float(pp.loc[pp["ph"].idxmin(), "f"])

    figb.update_xaxes(
        type="log",
        title_text="Frequency (Hz)",
        exponentformat="power",
        showexponent="all",
        dtick=1,
    )
    figb.update_yaxes(
        type="log",
        title_text="|Z| (Ω)",
        exponentformat="power",
        showexponent="all",
        dtick=1,
        secondary_y=False,
    )
    figb.update_yaxes(title_text="Phase angle (°)", secondary_y=True)
    if ph_all:
        vals = np.concatenate(ph_all)
        vals = vals[np.isfinite(vals)]
        if len(vals) and vals.max() > vals.min():
            _, _, step = _nice_axis(vals.max(), vals.min(), target=5)
            figb.update_yaxes(dtick=step, secondary_y=True)
    figb.update_layout(
        height=540,
        font=dict(size=13),
        margin=dict(l=80, r=70, t=50, b=60),
        legend=dict(
            orientation="h",
            x=0.5,
            xanchor="center",
            y=0.98,
            yanchor="top",
            bgcolor="rgba(255,255,255,0.65)",
            borderwidth=0,
        ),
    )
    bode_df = pd.concat(bode_rows, ignore_index=True) if bode_rows else None
    return figb, f_char, bode_df


def _make_mott_schottky_plot(datasets, area_cm2: float):
    fig = go.Figure()
    rows = []
    for idx, ds in enumerate(datasets):
        dd = pd.DataFrame(
            {"E": _num(ds["df"][ds["E"]]), "v": _num(ds["df"][ds["val"]])}
        ).dropna()
        if ds["is_inv"]:
            dd["y"] = dd["v"]
        else:
            dd["y"] = 1.0 / (dd["v"] ** 2)
        dd = dd.sort_values("E")
        if len(dd):
            fig.add_trace(
                go.Scatter(
                    x=dd["E"],
                    y=dd["y"] * (area_cm2 ** 2),
                    mode="lines+markers",
                    name=ds["label"],
                    line=dict(color=COLORWAY[idx % len(COLORWAY)], width=2),
                    marker=dict(size=6),
                )
            )
            rows.append(
                pd.DataFrame(
                    {
                        "dataset": ds["label"],
                        "E_V": dd["E"],
                        "inv_C2": dd["y"],
                    }
                )
            )
    fig.update_layout(
        xaxis_title="Potential E (V)",
        yaxis_title="1/C² (display scale)",
        height=520,
        font=dict(size=13),
        margin=dict(l=110, r=40, t=30, b=70),
    )
    return fig, (pd.concat(rows, ignore_index=True) if rows else None)


def _fit_nyquist_backend(ds, area_cm2: float, cfg: ApiConfig):
    freq = _num(ds["df"][ds["freq"]]) if ds["freq"] != "(none)" else None
    zr = _to_ohm(ds["df"][ds["zre"]], ds["unit"], area_cm2)
    zi = _to_ohm(ds["df"][ds["zim"]], ds["unit"], area_cm2)
    if ds["neg"]:
        zi = -zi
    payload = {
        "model": "Randles",
        "area_cm2": area_cm2,
        "data": pd.DataFrame(
            {
                "frequency_hz": freq,
                "z_real_ohm": zr,
                "z_imag_ohm": zi,
            }
        )
        .dropna()
        .to_dict(orient="records"),
    }
    return _request_private_api("/fit/eis", payload, cfg)


def _fit_ms_backend(payload: dict[str, Any], cfg: ApiConfig):
    return _request_private_api("/analyze/mott-schottky", payload, cfg)


def _band_payload_from_fit(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    sample = result.get("sample") or result.get("name") or "Sample"
    e_fb = (
        result.get("E_fb")
        or result.get("flat_band_potential")
        or result.get("x_intercept")
    )
    if e_fb is not None:
        rows.append(
            {
                "Material": sample,
                "Eg (eV)": 2.0,
                "Known edge": "CB",
                "Edge (V vs RHE)": float(e_fb),
            }
        )
    return rows


def _sidebar():
    st.sidebar.subheader("🔌 ElectroSim EIS")
    st.sidebar.caption("Impedance analysis — Nyquist · Bode · Mott–Schottky")
    st.sidebar.markdown("**Electrode & conditions**")
    area = st.sidebar.number_input(
        "Electrode area A (cm²)",
        min_value=1e-9,
        value=1.0,
        step=0.1,
        format="%.4g",
        key="eis_area_cm2",
    )
    with st.sidebar.expander("Kinetics for j₀ (optional)"):
        n_e = st.number_input(
            "Electrons transferred n",
            min_value=1,
            value=1,
            step=1,
            key="eis_n_e",
        )
        temp = st.number_input(
            "Temperature T (K)",
            min_value=1.0,
            value=298.15,
            step=1.0,
            format="%.2f",
            key="eis_temp",
        )
    with st.sidebar.expander("Figure style (journal)"):
        st.selectbox(
            "Font family",
            ["Arial", "Helvetica", "Times New Roman"],
            index=0,
            key="fig_font",
        )
        st.number_input(
            "Axis tick font size",
            min_value=8,
            max_value=48,
            value=28,
            step=2,
            key="fig_tick",
        )
        st.number_input(
            "Axis title font size",
            min_value=8,
            max_value=56,
            value=36,
            step=2,
            key="fig_title",
        )
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear all EIS data", key="clear_eis"):
        for key in list(st.session_state.keys()):
            if key in {
                "nyq_datasets",
                "bode_datasets",
                "ms_datasets",
                "ms_raw",
                "band_rows",
                "ms_results",
            } or "_fit" in key:
                st.session_state.pop(key, None)
        st.session_state["uploader_nonce"] = (
            st.session_state.get("uploader_nonce", 0) + 1
        )
        st.rerun()

    cfg = _load_api_config()
    if _api_ready(cfg):
        st.sidebar.success("Private backend connected via secrets")
    else:
        st.sidebar.info("Private backend not configured yet")
    st.session_state.setdefault("uploader_nonce", 0)
    return area, n_e, temp, cfg, st.session_state["uploader_nonce"]


def _nyquist_tab(area: float, cfg: ApiConfig, nonce: int) -> None:
    up = st.container()
    an = st.container()

    with up:
        st.info(
            "**📥 Upload Nyquist data here** — files with Z′ and Z″ columns."
            " A frequency column enables Kramers–Kronig and fit actions."
        )
        files = st.file_uploader(
            "Nyquist data files",
            type=SUPPORTED_EXTENSIONS,
            accept_multiple_files=True,
            key=f"nyq_up_{nonce}",
        )
        datasets = []
        if files:
            for idx, uf in enumerate(files):
                df = _read_eis_file(uf)
                if df is None or df.shape[1] < 2:
                    st.error(f"❌ {uf.name}: could not parse ≥2 columns.")
                    continue
                roles = _detect_impedance_columns(df)
                unit_guess = _guess_unit_label(
                    roles["zreal"] or str(df.columns[0])
                )
                with st.expander(
                    f"🗂 {uf.name} — columns auto-detected",
                    expanded=False,
                ):
                    cols = df.columns.tolist()
                    opts = ["(none)"] + cols
                    c1, c2, c3 = st.columns(3)
                    zre = c1.selectbox(
                        "Z′ real",
                        opts,
                        index=_role_idx(cols, roles["zreal"]),
                        key=f"nyq_zre_{nonce}_{idx}",
                    )
                    zim = c2.selectbox(
                        "Z″ imaginary",
                        opts,
                        index=_role_idx(cols, roles["zimag"]),
                        key=f"nyq_zim_{nonce}_{idx}",
                    )
                    fr = c3.selectbox(
                        "Frequency (Hz, optional)",
                        opts,
                        index=_role_idx(cols, roles["freq"]),
                        key=f"nyq_f_{nonce}_{idx}",
                    )
                    c4, c5 = st.columns(2)
                    unit = c4.selectbox(
                        "Impedance unit",
                        list(UNIT_MAP.keys()),
                        index=list(UNIT_MAP.keys()).index(unit_guess),
                        key=f"nyq_u_{nonce}_{idx}",
                    )
                    neg = c5.checkbox(
                        "Imaginary column already stores −Z″",
                        value=bool(roles["zimag_negated"]),
                        key=f"nyq_neg_{nonce}_{idx}",
                    )
                    st.dataframe(_arrow_safe(df.head(12)), width="stretch")
                if zre != "(none)" and zim != "(none)":
                    datasets.append(
                        {
                            "name": uf.name,
                            "df": df,
                            "zre": zre,
                            "zim": zim,
                            "freq": fr,
                            "unit": unit,
                            "neg": neg,
                        }
                    )
                else:
                    st.warning(f"{uf.name}: map both Z′ and Z″ to use it.")
            st.session_state["nyq_datasets"] = datasets
        elif st.session_state.get("nyq_datasets"):
            count = len(st.session_state["nyq_datasets"])
            st.info(
                f"{count} dataset(s) loaded. Upload new files to replace them."
            )

    with an:
        datasets = st.session_state.get("nyq_datasets") or []
        if not datasets:
            st.info("Upload Nyquist data in the uploader above first.")
            return

        st.subheader("Nyquist plot (−Z″ vs Z′)")
        fig, nyq_df = _make_nyquist_plot(datasets, area)
        _pchart(fig, width="content")
        _plot_downloads(fig, "nyquist_overlay", data_df=nyq_df)

        st.subheader("Landmarks")
        land = []
        for ds in datasets:
            zr = _to_ohm(ds["df"][ds["zre"]], ds["unit"], area).dropna()
            if not len(zr):
                continue
            zr_pos = zr[zr > 0]
            rs = float(zr_pos.min()) if len(zr_pos) else float(zr.min())
            rmax = float(zr.max())
            land.append(
                {
                    "Dataset": ds["name"],
                    "Rs≈ intercept (Ω)": rs,
                    "Rct≈ Z′ span (Ω)": rmax - rs,
                    "Rs·A (Ω·cm²)": rs * area,
                    "Rct·A (Ω·cm²)": (rmax - rs) * area,
                }
            )
        if land:
            st.dataframe(_arrow_safe(pd.DataFrame(land)), width="stretch")

        st.subheader("Kramers–Kronig & circuit fit")
        names = [ds["name"] for ds in datasets]
        sel = st.selectbox("Dataset to fit", names, key=f"nyq_fit_sel_{nonce}")
        ds = datasets[names.index(sel)]
        if ds["freq"] == "(none)":
            st.warning(
                "This dataset has no frequency column. The public app can "
                "still plot it, but the private fit needs frequency."
            )
        if st.button("▶ Fit Nyquist circuit", key=f"nyq_fitbtn_{nonce}"):
            if not _api_ready(cfg):
                st.warning("Add private API secrets to run fitting.")
            else:
                try:
                    result = _fit_nyquist_backend(ds, area, cfg)
                    st.success("Fit completed.")
                    st.json(result)
                except Exception as exc:
                    st.error(f"Fit failed: {exc}")


def _bode_tab(area: float, nonce: int) -> None:
    up = st.container()
    an = st.container()

    with up:
        st.info(
            "**📥 Upload Bode data here** — files of frequency vs |Z| and/or "
            "phase. Separate magnitude and phase files can be matched by "
            "frequency."
        )
        files = st.file_uploader(
            "Bode data files",
            type=SUPPORTED_EXTENSIONS,
            accept_multiple_files=True,
            key=f"bode_up_{nonce}",
        )
        datasets = []
        if files:
            for idx, uf in enumerate(files):
                df = _read_eis_file(uf)
                if df is None or df.shape[1] < 2:
                    st.error(f"❌ {uf.name}: could not parse ≥2 columns.")
                    continue
                roles = _detect_impedance_columns(df)
                unit_guess = _guess_unit_label(
                    roles["zreal"] or str(df.columns[-1])
                )
                with st.expander(
                    f"🗂 {uf.name} — columns auto-detected",
                    expanded=False,
                ):
                    cols = df.columns.tolist()
                    opts = ["(none)"] + cols
                    c1, c2, c3 = st.columns(3)
                    fr = c1.selectbox(
                        "Frequency (Hz)",
                        opts,
                        index=_role_idx(cols, roles["freq"]),
                        key=f"bode_f_{nonce}_{idx}",
                    )
                    zm = c2.selectbox(
                        "|Z| magnitude",
                        opts,
                        index=_role_idx(cols, roles["zreal"]),
                        key=f"bode_zm_{nonce}_{idx}",
                    )
                    ph = c3.selectbox(
                        "Phase angle",
                        opts,
                        index=_role_idx(cols, roles["zimag"]),
                        key=f"bode_ph_{nonce}_{idx}",
                    )
                    c4, c5 = st.columns(2)
                    unit = c4.selectbox(
                        "|Z| unit",
                        list(UNIT_MAP.keys()),
                        index=list(UNIT_MAP.keys()).index(unit_guess),
                        key=f"bode_u_{nonce}_{idx}",
                    )
                    ph_unit = c5.radio(
                        "Phase unit",
                        ["degrees", "radians"],
                        horizontal=True,
                        key=f"bode_pu_{nonce}_{idx}",
                    )
                    st.dataframe(_arrow_safe(df.head(12)), width="stretch")
                if fr != "(none)" and (zm != "(none)" or ph != "(none)"):
                    datasets.append(
                        {
                            "name": uf.name,
                            "df": df,
                            "freq": fr,
                            "zmod": zm,
                            "phase": ph,
                            "unit": unit,
                            "phase_unit": ph_unit,
                        }
                    )
                else:
                    st.warning(
                        f"{uf.name}: map Frequency and at least one of |Z| or "
                        "Phase."
                    )
            st.session_state["bode_datasets"] = datasets
        elif st.session_state.get("bode_datasets"):
            count = len(st.session_state["bode_datasets"])
            st.info(
                f"{count} dataset(s) loaded. Upload new files to replace them."
            )

    with an:
        datasets = st.session_state.get("bode_datasets") or []
        if not datasets:
            st.info("Upload Bode data in the uploader above first.")
            return

        st.subheader("Bode plot — |Z| and phase vs frequency")
        figb, f_char, bode_df = _make_bode_plot(datasets, area)
        _pchart(figb, width="stretch")
        if f_char is not None:
            st.caption(
                f"Characteristic frequency (phase extremum) ≈ {f_char:.4g} Hz."
            )
        _plot_downloads(figb, "bode_plot", data_df=bode_df)
        st.subheader("Bode interpretation")
        st.markdown(
            "- High-frequency |Z| tends toward Rs.\n"
            "- Low-frequency |Z| tends toward Rs + Rct.\n"
            "- Phase near −90° indicates a strong capacitive response."
        )


def _mott_schottky_tab(
    area: float,
    n_e: int,
    temp: float,
    cfg: ApiConfig,
    nonce: int,
) -> None:
    up = st.container()
    an = st.container()

    with up:
        st.info(
            "**📥 Upload Mott–Schottky data here.** Summary files use "
            "Potential vs 1/C² (or raw C); the app can also accept raw "
            "per-potential spectra."
        )
        files = st.file_uploader(
            "Mott–Schottky files",
            type=SUPPORTED_EXTENSIONS,
            accept_multiple_files=True,
            key=f"ms_up_{nonce}",
        )
        datasets = []
        if files:
            for idx, uf in enumerate(files):
                df = _read_eis_file(uf)
                if df is None or df.shape[1] < 2:
                    st.error(f"❌ {uf.name}: could not parse ≥2 columns.")
                    continue
                roles = _detect_ms_columns(df)
                with st.expander(
                    f"🗂 {uf.name} — columns auto-detected",
                    expanded=False,
                ):
                    cols = df.columns.tolist()
                    opts = ["(none)"] + cols
                    c1, c2, c3 = st.columns(3)
                    ep = c1.selectbox(
                        "Potential E (V)",
                        opts,
                        index=_role_idx(cols, roles["potential"]),
                        key=f"ms_e_{nonce}_{idx}",
                    )
                    val = c2.selectbox(
                        "Capacitance or 1/C²",
                        opts,
                        index=_role_idx(cols, roles["value"]),
                        key=f"ms_v_{nonce}_{idx}",
                    )
                    is_inv = c3.checkbox(
                        "Column is 1/C² (F⁻²)",
                        value=bool(roles["value_is_inv_sq"]),
                        key=f"ms_inv_{nonce}_{idx}",
                    )
                    st.dataframe(_arrow_safe(df.head(12)), width="stretch")
                if ep != "(none)" and val != "(none)":
                    datasets.append(
                        {
                            "name": uf.name,
                            "df": df,
                            "E": ep,
                            "val": val,
                            "is_inv": is_inv,
                            "label": uf.name,
                        }
                    )
                else:
                    st.warning(
                        f"{uf.name}: map both potential and capacitance/1-C²."
                    )
            st.session_state["ms_datasets"] = datasets
        elif st.session_state.get("ms_datasets"):
            count = len(st.session_state["ms_datasets"])
            st.info(
                f"{count} dataset(s) loaded. Upload new files to replace them."
            )

    with an:
        datasets = st.session_state.get("ms_datasets") or []
        if not datasets:
            st.info("Upload Mott–Schottky data in the uploader above first.")
            return

        st.subheader("Mott–Schottky plot (1/C² vs E)")
        fig, ms_df = _make_mott_schottky_plot(datasets, area)
        _pchart(fig, width="stretch")
        _plot_downloads(fig, "mott_schottky", data_df=ms_df)

        st.subheader("Linear depletion-region fit")
        st.caption(
            "Pick the linear depletion region and fit to extract flat-band "
            "potential and carrier density."
        )
        for idx, ds in enumerate(datasets):
            st.markdown(f"#### {ds['name']}")
            dd = pd.DataFrame(
                {
                    "E": _num(ds["df"][ds["E"]]),
                    "v": _num(ds["df"][ds["val"]]),
                }
            ).dropna()
            if not len(dd):
                st.warning("No usable points found.")
                continue
            st.dataframe(_arrow_safe(dd.head(30)), width="stretch")
            if st.button("▶ Fit Mott-Schottky", key=f"ms_fit_{nonce}_{idx}"):
                if not _api_ready(cfg):
                    st.warning("Add private API secrets to run this fit.")
                else:
                    try:
                        payload = {
                            "sample": ds["name"],
                            "data": dd.to_dict(orient="records"),
                            "area_cm2": area,
                            "temperature_K": temp,
                            "n_electrons": n_e,
                        }
                        result = _fit_ms_backend(payload, cfg)
                        st.success("Fit completed.")
                        st.json(result)
                        st.session_state.setdefault("ms_results", {})[
                            ds["name"]
                        ] = result
                    except Exception as exc:
                        st.error(f"Fit failed: {exc}")


def _band_tab(area: float) -> None:
    st.subheader("Band diagram / energy levels")
    st.markdown(
        "Import Mott–Schottky results or build a simple band diagram from "
        "fitted flat-band values."
    )
    ms_results = st.session_state.get("ms_results", {})
    if ms_results:
        rows = []
        for result in ms_results.values():
            rows.extend(_band_payload_from_fit(result))
        if rows:
            st.dataframe(pd.DataFrame(rows), width="stretch")
    else:
        st.info(
            "Fit one or more Mott–Schottky datasets to populate the band "
            "diagram."
        )


def _tutorials_tab() -> None:
    st.header("📚 Tutorials & learning resources")
    st.markdown(
        r'''
## Overview

EIS probes a system by applying a small sinusoidal potential perturbation over
frequencies and measuring complex current response.

## Background & key equations

**Complex impedance** as a function of angular frequency $\omega = 2\pi f$:

$$Z(\omega) = Z' + jZ'', \qquad |Z| = \sqrt{Z'^2 + Z''^2},$$
$$\varphi = \arctan\!\left(\frac{Z''}{Z'}\right)$$

**Element impedances:**

$$Z_R = R, \qquad Z_C = \frac{1}{j\omega C},$$
$$Z_{\text{CPE}} = \frac{1}{Q\,(j\omega)^{n}}, \qquad Z_W =
\frac{\sigma}{\sqrt{\omega}}(1 - j)$$

**Randles circuit:**

$$Z = R_s + \cfrac{1}{\,j\omega C_{dl} + \cfrac{1}{R_{ct} + Z_W}\,}$$

**Mott–Schottky relation:**

$$\frac{1}{C^2} = \frac{2}{e\,\varepsilon\,\varepsilon_0 A^2 N}
\left(E - E_{FB} - \frac{kT}{e}\right)$$

## App structure

Each measurement type has its own analyzer tab with upload and analysis
sections, matching the private suite flow.
        '''
    )


def main() -> None:
    st.set_page_config(
        page_title="ElectroSim EIS",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    area, n_e, temp, cfg, nonce = _sidebar()

    st.title("🔌 ElectroSim EIS")
    st.caption(
        "Upload instrument exports — each analyzer tab holds its uploader and "
        "analysis together and accepts multiple files."
    )

    nyq_tab, bode_tab, ms_tab, band_tab, tut_tab = st.tabs(
        [
            "🟦 Nyquist",
            "🟥 Bode",
            "🟩 Mott–Schottky",
            "📊 Band diagram",
            "📚 Tutorials",
        ]
    )

    with nyq_tab:
        _nyquist_tab(area, cfg, nonce)
    with bode_tab:
        _bode_tab(area, nonce)
    with ms_tab:
        _mott_schottky_tab(area, n_e, temp, cfg, nonce)
    with band_tab:
        _band_tab(area)
    with tut_tab:
        _tutorials_tab()


if __name__ == "__main__":
    main()
