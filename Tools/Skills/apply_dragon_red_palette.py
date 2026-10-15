"""Install the current red-dominant Dragon Breath RGB palette only."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dragon_volume_color
importlib.reload(build_dragon_volume_color).run_color_only()
