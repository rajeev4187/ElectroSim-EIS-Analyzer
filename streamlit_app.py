"""Compatibility Streamlit launcher.

Prefer deploying with ElectroSim-EIS.py as the main file path.
This shim forwards to that canonical entrypoint for Cloud defaults.
"""

from __future__ import annotations

import runpy
from pathlib import Path

APP_PATH = Path(__file__).parent / "ElectroSim-EIS.py"

runpy.run_path(str(APP_PATH), run_name="__main__")
