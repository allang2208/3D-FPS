"""Restore the three authored imagegen icons without changing their composition."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
for element in ('fire','ice','lightning'):
    name=f'elemental_arrow_{element}.png'
    shutil.copy2(ROOT/'SourceAssets/ElementalArrow20261027'/name,ROOT/'Content/ColdSteelData/Skills'/name)
