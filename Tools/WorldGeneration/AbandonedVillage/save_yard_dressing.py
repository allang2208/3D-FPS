"""Update just the outdoor dressing in the already-authored village sublevel."""
import hashlib
import json
from pathlib import Path
import sys

import unreal as u

sys.path.insert(0,str(Path(__file__).resolve().parent))
from village_yard_dressing import build_yard_dressing
from wall_support import fit_plan

root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
source = root/'SourceAssets/TemperateHillsVillage'
plan = fit_plan(json.loads((source/'layout.json').read_text(encoding='utf-8')))
kit = json.loads((source/'house-pieces.json').read_text(encoding='utf-8'))
level = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
asset = root/'Content'/(level.removeprefix('/Game/')+'.umap')
before = hashlib.sha256(asset.read_bytes()).digest()
world = u.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Cannot load '+level)
report = build_yard_dressing(world,source,plan,kit)
if before!=hashlib.sha256(asset.read_bytes()).digest():
    raise RuntimeError('Village level changed on disk while authoring yards')
if not u.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Could not save '+level)
u.log('VILLAGE_YARDS_SAVED '+json.dumps(report))
