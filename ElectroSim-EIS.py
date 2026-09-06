"""ElectroSim-EIS Analyzer — Streamlit entry point.

Deploy on Streamlit Community Cloud with this file as the main file path.
Run locally with:

    streamlit run ElectroSim-EIS.py

This is the only source file in the repository. It is a thin loader: the
analysis engine is published as compiled Python bytecode in version-suffixed
files under ``release/web-demo``:

    eis_engine.cp312.pyc   <- for Python 3.12
    eis_engine.cp313.pyc   <- for Python 3.13 (Streamlit Cloud default)
    eis_engine.cp314.pyc   <- for Python 3.14
    eis_engine.cpXY.pyc    <- generally, ".cp" + major + minor

The loader picks the .pyc matching the running Python and exec()s its
bytecode in this module's global scope, so ``streamlit run`` behaves exactly
as if the engine source were written here.

Why one file per version? A .pyc is keyed to the exact interpreter version
(its "magic number"), so a build for 3.12 will not load on 3.14 and vice
versa. Streamlit Cloud pins a Python version while local maintainer testing
runs on whatever is in the dev venv — shipping one .pyc per target is the
simplest way both paths work without publishing the source.

Maintainers: regenerate all three artifacts from the private upstream
sources with ``build_web_engine.py`` in the upstream app folder
(``py -3.12 build_web_engine.py``, or ``--all`` for every target). That
script merges the engine's two modules, checks their namespaces are safe to
merge, and writes the .pyc files straight into ``release/web-demo``.
"""
from __future__ import annotations

import marshal
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_HERE, "release", "web-demo")


def _verify_under_streamlit_run() -> None:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        sys.stderr.write(
            "\n[ElectroSim-EIS] Streamlit is not installed in this "
            "Python.\n"
            "  Install it first:    pip install -r requirements.txt\n"
            "  Then launch with:    streamlit run "
            + os.path.basename(__file__) + "\n\n"
        )
        sys.exit(1)
    if get_script_run_ctx() is None:
        sys.stderr.write(
            "\n[ElectroSim-EIS] This script must be launched with "
            "`streamlit run`, not plain `python`.\n\n"
            "  WRONG:  python " + os.path.basename(__file__) + "\n"
            "  RIGHT:  streamlit run " + os.path.basename(__file__)
            + "\n\n"
            "Reason: the analysis engine calls st.set_page_config / "
            "st.sidebar / etc. at\nmodule load time, which need "
            "Streamlit's per-thread ScriptRunContext.\nThat context "
            "is only set up by `streamlit run`.\n\n"
        )
        sys.exit(1)


def _available_versions() -> list[str]:
    """Python-version tags for every engine .pyc shipped in this deployment."""
    tags = []
    for name in os.listdir(_ENGINE_DIR):
        if name.startswith("eis_engine.cp") and name.endswith(".pyc"):
            tags.append(name[len("eis_engine."):-len(".pyc")])
    return sorted(tags)


def _load_engine_code():
    py_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    pyc = os.path.join(_ENGINE_DIR, f"eis_engine.{py_tag}.pyc")

    if not os.path.isfile(pyc):
        shipped = ", ".join(_available_versions()) or "none"
        raise FileNotFoundError(
            f"No engine bytecode for Python {sys.version_info.major}."
            f"{sys.version_info.minor} (looked for eis_engine.{py_tag}.pyc). "
            f"This deployment ships .pyc for: {shipped}. Either run with one "
            f"of those Python versions, or rebuild the engine for "
            f"{sys.version_info.major}.{sys.version_info.minor} with "
            f"build_web_engine.py in the upstream app folder."
        )

    # Python >=3.7 .pyc header is 16 bytes: 4-byte magic + 4-byte flags +
    # 8-byte source-hash-or-mtime+size. The rest is the marshalled code object.
    with open(pyc, "rb") as fh:
        blob = fh.read()
    try:
        return marshal.loads(blob[16:])
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load {os.path.basename(pyc)}. The file is named for "
            f"Python {py_tag} but its bytecode header did not validate — most "
            f"likely it was built by a different interpreter and renamed by "
            f"hand. Rebuild it with the matching Python."
        ) from exc


_verify_under_streamlit_run()
exec(_load_engine_code(), globals())

# The engine bytecode carries no citation text. Appending it here keeps the
# citation editable without rebuilding the .pyc files.
import streamlit as _st

_st.sidebar.markdown("---")
_st.sidebar.caption(
    "**Cite this tool:** Kumar, R. (2026). *ElectroSim-EIS Analyzer* "
    "(V2.0) [Computer software]. North Carolina Central University. "
    "Zenodo. https://doi.org/10.5281/zenodo.22447886"
)
