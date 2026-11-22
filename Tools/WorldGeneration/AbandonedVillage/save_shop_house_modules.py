"""Publish wall bays and deck edges, then attach native modules to plots 06 and 09."""
import json
import os
from pathlib import Path
import shutil
import sys

import unreal as u

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE),str(HERE.parent/'VillageBakery')]
from author_shop_house_modules import bakery_bays, gunshop_edges
from bakery_shell import install_bakery_masonry
from install_shop_house_modules import replace_modules
from shop_house_modules import HILLS, gunshop_modules

out = Path(os.environ['BAKERY_LEVEL_RUN'])
report = {}
for key,make in (('bakery_bays',bakery_bays),('gunshop_edges',gunshop_edges)):
    report[key] = make()
    (out/(key+'.json')).write_text(json.dumps(report[key],indent=2),encoding='utf-8')
    u.SystemLibrary.collect_garbage()

level = HILLS+'AbandonedVillage/L_AbandonedVillage'
package = ROOT/'Content'/(level.removeprefix('/Game/')+'.umap')
stamp = package.stat().st_mtime_ns
shutil.copy2(package,out/'Village.before.umap')
world = u.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Could not open the current village')
actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
report['bakery'] = install_bakery_masonry(actors)
report['gunshop'] = replace_modules(actors,'VillageGunshop',gunshop_modules(),
                                    {HILLS+'VillageGunshop/Architecture/SM_Gunshop_Floors'})
if stamp != package.stat().st_mtime_ns:
    raise RuntimeError('The village changed on disk during authoring')
if not u.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Could not save the village level')
report.update(level=level,runtime_tested=False)
(out/'level-saved.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
