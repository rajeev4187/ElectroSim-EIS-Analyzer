"""Compatibility Streamlit launcher.

This shim resolves to the private GUI first when available, then falls back
to the canonical entrypoint in this repo.
"""

from __future__ import annotations

import runpy
from pathlib import Path

PRIVATE_APP_PATH = Path(
    r"E:/GitHub repos done/Working-Apps/EIS/ElectroSim-EIS.py"
)
PUBLIC_APP_PATH = Path(__file__).parent / "ElectroSim-EIS.py"
APP_PATH = PRIVATE_APP_PATH if PRIVATE_APP_PATH.exists() else PUBLIC_APP_PATH

runpy.run_path(str(APP_PATH), run_name="__main__")
