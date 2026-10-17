"""Restore the authored icon; no generated substitute or placeholder."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[2]
shutil.copy2(root/'SourceAssets/IceArmor20261017/ice_armor_cold_steel.png',root/'Content/ColdSteelData/Skills/ice_armor_cold_steel.png')
