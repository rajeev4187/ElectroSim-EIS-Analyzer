"""Root Streamlit launcher for Streamlit Community Cloud defaults.

This shim loads the real app from release/web-demo so deployments work even
when the app path is not explicitly configured in Streamlit settings.
"""

from __future__ import annotations

import runpy
from pathlib import Path

APP_PATH = Path(__file__).parent / "release" / "web-demo" / "ElectroSim-EIS.py"

runpy.run_path(str(APP_PATH), run_name="__main__")
