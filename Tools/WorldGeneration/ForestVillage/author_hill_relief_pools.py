"""Bake the R28 region and closed pools before rebuilding their PCG and grass layers."""
import csv
import json
import os
from pathlib import Path
import unreal as u

src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])
batch=Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])
target='/Game/GameMaps/L_ForestPathVillage'
save=u.EditorLoadingAndSavingUtils
def bake_terrain():
    world=save.load_map(target)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name('L_ForestPathVillage'):
        raise RuntimeError('Persistent forest village level is required')
    region=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.ForestVillageRegion))
    hill=json.loads((src/'hill.json').read_text())
    if not region.install_hill_site(str(src),u.IntPoint(*hill['site_min_m']),hill['village_datum_cm']):
        raise RuntimeError('Settlement surface could not be installed')
    mat=u.load_asset('/Game/ForestPathStudy/VillageRegion/Reference/MI_ForestReference')
    if not region.bake_reference_surface(str(src),mat):raise RuntimeError('Region tiles/collision failed to bake')
    if not region.bake_woodland_pools(str(src/'Grass'),237855):raise RuntimeError('No viable closed pools')
    with (src/'Grass/ponds.csv').open(encoding='utf-8-sig') as f:pools=list(csv.DictReader(f))
    if not save.save_map(world,target):raise RuntimeError('Cannot save terrain and pool sites')
    (batch/'terrain.json').write_text(json.dumps({'pools':pools,'count':len(pools)},indent=2))


def build_all():
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from author_relief_woodland import install
    bake_terrain()
    install()

if __name__=='__main__':build_all()
