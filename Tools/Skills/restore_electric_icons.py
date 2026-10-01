"""Restore the two saved imagegen icons to their current runtime filenames."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'SourceAssets/ElectricMagic20261001/Icons'
DEST=ROOT/'Content/ColdSteelData/Skills'
DEST.mkdir(parents=True,exist_ok=True)
for name in ('storm_domain_cold_steel.png','thunder_lance_cold_steel.png'):
    shutil.copy2(SOURCE/name,DEST/name)
    print('Saved '+str(DEST/name))
