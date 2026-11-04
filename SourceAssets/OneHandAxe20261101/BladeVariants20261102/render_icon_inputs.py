"""Render three real-model inputs for imagegen; this does not author final framed icons."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent/'ContinuousBladesR5_20261104/render_icon_inputs.py'),run_name='__main__')
