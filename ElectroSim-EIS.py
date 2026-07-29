"""Canonical Streamlit entrypoint for ElectroSim-EIS Analyzer.

It forwards execution to the private GUI when that repo is present locally,
otherwise it falls back to the public web-demo implementation.
"""

from __future__ import annotations

import runpy
from pathlib import Path

PRIVATE_APP_PATH = Path(
    r"E:/GitHub repos done/Working-Apps/EIS/ElectroSim-EIS.py"
)
PUBLIC_APP_PATH = (
    Path(__file__).parent / "release" / "web-demo" / "ElectroSim-EIS.py"
)
APP_PATH = PRIVATE_APP_PATH if PRIVATE_APP_PATH.exists() else PUBLIC_APP_PATH

runpy.run_path(str(APP_PATH), run_name="__main__")
