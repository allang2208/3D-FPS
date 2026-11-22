"""Apply the bakery and tavern roof work to the latest saved village only."""
import json
import os
from pathlib import Path
import shutil
import sys

import unreal as ue

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'VillageTavern'))
from install_bakery import install_bakery
from install_chimney import install_chimney
from village_chimney import install_village_hearths

LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
out = Path(os.environ['BAKERY_LEVEL_RUN'])
source = ROOT/'SourceAssets/TemperateHillsVillage'
package = ROOT/'Content'/(LEVEL.removeprefix('/Game/')+'.umap')
stamp = package.stat().st_mtime_ns
shutil.copy2(package,out/'Village.before.umap')
plan = json.loads((source/'layout.json').read_text(encoding='utf-8'))
kit = json.loads((source/'house-pieces.json').read_text(encoding='utf-8'))
world = ue.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:
    raise RuntimeError('Could not load the village')
actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)
report = {'bakery':install_bakery(actors,plan,kit)}
if os.environ.get('BAKERY_LEVEL_ONLY') != '1':
    report['tavern_chimney'] = install_chimney(actors,plan,kit)
    report['village_hearths'] = install_village_hearths(actors,plan,kit)
if stamp != package.stat().st_mtime_ns:
    raise RuntimeError('Village package changed during authoring. Rerun from the updated map.')
if not ue.EditorLoadingAndSavingUtils.save_map(world,LEVEL):
    raise RuntimeError('Failed to save '+LEVEL)
report.update(level=LEVEL,runtime_tested=False)
(out/'level-saved.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
