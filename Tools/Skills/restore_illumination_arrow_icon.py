"""Restore the selected imagegen source, then use author_illumination_arrow.py to import."""
from pathlib import Path
import shutil
R=Path(__file__).resolve().parents[2]
shutil.copy2(R/'SourceAssets/IlluminationArrow20261027/illumination_arrow_cold_steel.png',R/'Content/ColdSteelData/Skills/illumination_arrow_cold_steel.png')
