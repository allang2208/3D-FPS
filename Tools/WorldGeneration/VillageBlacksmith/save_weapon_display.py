"""Refresh only the smith's display assemblies in the current village package."""
import json
import shutil
import sys
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from forge_weapon_display import install_forge_display

LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
map_file = (ROOT / 'Content' / LEVEL.removeprefix('/Game/')).with_suffix('.umap')
timestamp = map_file.stat().st_mtime_ns
backup = ROOT / 'Saved/VillageWorkshopDisplays/Before' / str(timestamp) / map_file.name
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(map_file, backup)

receipt = ROOT / 'SourceAssets/HillsVillageCarpenter/workshop-displays-saved.json'
report = json.loads(receipt.read_text(encoding='utf-8'))
world = u.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:
    raise RuntimeError('Could not load ' + LEVEL)
report['01'] = install_forge_display()
if map_file.stat().st_mtime_ns != timestamp:
    raise RuntimeError('Village changed during assembly. Reload before saving.')
if not u.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
    raise RuntimeError('Could not save ' + LEVEL)
receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('FORGE_DISPLAY_SAVED ' + json.dumps(report['01']))
