"""Publish the current Farreach slender revision."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name("publish_slim.py")),run_name="__main__")
