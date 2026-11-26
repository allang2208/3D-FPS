"""Save the village upgrade in a background editor commandlet after native builds."""
from pathlib import Path
import os
import runpy
import shutil

ROOT = Path(__file__).resolve().parents[3]
BACKUP = ROOT / 'SourceAssets/TemperateHillsVillage/Upgrade20261114/Before'
for relative in (
    'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap',
    'Content/WorldGeneration/TemperateHills/AbandonedVillage/T_VillageRoadMask.uasset',
):
    original = ROOT / relative
    target = BACKUP / relative
    if original.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)

os.environ['VILLAGE_REUSE_ROAD_MATERIAL'] = '1'
runpy.run_path(str(Path(__file__).with_name('author_village.py')), run_name='__main__')
