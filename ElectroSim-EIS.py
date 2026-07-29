"""Canonical Streamlit entrypoint for ElectroSim-EIS Analyzer.

Deploy Streamlit Community Cloud with this file as the main script.
It forwards execution to the maintained web-demo implementation, which
loads the analysis engine from compiled bytecode (see release/web-demo).
"""

from __future__ import annotations

import runpy
from pathlib import Path

APP_PATH = Path(__file__).parent / "release" / "web-demo" / "ElectroSim-EIS.py"

runpy.run_path(str(APP_PATH), run_name="__main__")
