"""Patch the materials of existing yard instances and the single bakery shell in place."""
import json
import os
from pathlib import Path
import shutil
import sys

import unreal as ue

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE.parent/'VillageBakery'), str(HERE.parent/'AbandonedVillage')]
from bakery_shell import install_bakery_masonry
from yard_house_masonry import update_existing_yards

LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
out = Path(os.environ['BAKERY_LEVEL_RUN'])
source = ROOT/'Content'/(LEVEL.removeprefix('/Game/')+'.umap')
stamp = source.stat().st_mtime_ns
shutil.copy2(source, out/'Village.before.umap')
world = ue.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:
    raise RuntimeError('Could not open saved village')
actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)
report = dict(level=LEVEL, bakery=install_bakery_masonry(actors), yard_instances=update_existing_yards(actors))
if not report['yard_instances']:
    raise RuntimeError('No authored courtyard wall components found')
if source.stat().st_mtime_ns != stamp:
    raise RuntimeError('Village changed during authoring; repeat against the latest saved level')
if not ue.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
    raise RuntimeError('Could not save '+LEVEL)
(out/'level-saved.json').write_text(json.dumps(report, ensure_ascii=False, indent=2),encoding='utf-8')
