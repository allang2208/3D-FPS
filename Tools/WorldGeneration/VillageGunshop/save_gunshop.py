"""Apply only the gunshop to the latest saved abandoned village sublevel."""
import json
import os
from pathlib import Path
import shutil
import sys

import unreal as ue

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0,str(HERE))
from install_gunshop import install_gunshop
from gunshop_furnish_author import publish

level = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
out = Path(os.environ['BAKERY_LEVEL_RUN'])
source = ROOT/'SourceAssets/TemperateHillsVillage'
package = ROOT/'Content'/(level.removeprefix('/Game/')+'.umap')
stamp = package.stat().st_mtime_ns
shutil.copy2(package,out/'Village.before.umap')
plan = json.loads((source/'layout.json').read_text(encoding='utf-8'))
kit = json.loads((source/'house-pieces.json').read_text(encoding='utf-8'))
world = ue.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Could not load '+level)
actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)
new_fixtures = publish(only={'CounterTray'})
report = install_gunshop(actors,plan,kit)
report['authored_fixtures'] = new_fixtures
if package.stat().st_mtime_ns != stamp:
    raise RuntimeError('Village changed on disk during authoring. Reload the latest package.')
if not ue.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Failed to save '+level)
report['level'] = level
(out/'level-saved.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
