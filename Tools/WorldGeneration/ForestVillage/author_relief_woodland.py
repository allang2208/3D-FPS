"""Reproject forest PCG, wet-bank planting and global grass coverage onto the final relief."""
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import unreal as u

tools=Path(__file__).resolve().parent
sys.path.insert(0,str(tools))
import author_grass_distance as grass_distance
import author_trail_cover_level as level
import author_trail_cover_materials as art

def install(*,reselect=False):
    src,batch=level.src,level.batch
    world=level.save.load_map(level.village)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name('L_ForestPathVillage'):
        raise RuntimeError('Persistent forest village level is required')
    actors=level.actor_list()
    region=next(a for a in actors if isinstance(a,u.ForestVillageRegion))
    if reselect and not region.bake_woodland_pools(str(src/'Grass'),237855):
        raise RuntimeError('No viable closed pool layout')
    with (src/'Grass/ponds.csv').open(encoding='utf-8-sig') as f:pools=list(csv.DictReader(f))
    # Pass the actual exported flood/shore raster to the normal offline grass pipeline.
    python=os.environ.get('FPS_TERRAIN_PYTHON') or shutil.which('py')
    if not python:raise RuntimeError('Set FPS_TERRAIN_PYTHON to an interpreter with NumPy, SciPy and Pillow')
    args=[python]+(['-3.11'] if Path(python).name.lower() in ('py','py.exe') else [])
    env={k:v for k,v in os.environ.items() if k not in ('PYTHONHOME','PYTHONPATH')}
    subprocess.run(args+[str(tools/'prepare_relief_woodland.py'),str(src.parent),str(src)],check=True,env=env)
    templates=[c for a in actors if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name()
               for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
    placement=src/'Grass/planting.bin'
    if u.EditorAssetLibrary.does_asset_exist('/Game/ForestPathStudy/VillageRegion/WoodlandDressing/M_WoodlandScan'):
        import author_roadside_leaves as litter
        dressing=batch/'WoodlandDressing'
        subprocess.run(args+[str(tools/'prepare_forest_litter.py'),str(src.parent/'ForestLitter-R29'),str(src),str(dressing),'--points-only'],check=True,env=env)
        litter.textures(dressing,field_only=True)
        placement=dressing/'planting.bin'
    if not templates or not region.bake_vegetation(str(placement),templates):
        raise RuntimeError('Vegetation or PCG pool surfaces incomplete')
    if not region.install_grass_cover(str(src/'Grass/near_grass.u8')):
        raise RuntimeError('Near grass could not be baked')
    shores=grass_distance.rebuild(world,region,sedge_only=True)
    count,cells=level.place_meadows(world)
    dest=art.ref+'/ContinuousMeadow'
    field=art.tex('T_ContinuousMeadowField',dest,'BC7',False)
    for key in ('address_x','address_y'):field.set_editor_property(key,u.TextureAddress.TA_CLAMP)
    field.set_editor_property('compression_no_alpha',False);art.save(field)
    water_actors=[a for a in level.actor_list() if isinstance(a,u.ForestVillagePoolSurface) and a.get_path_name().startswith(level.village+'.')]
    if len(water_actors)!=len(pools):raise RuntimeError('PCG pool actor count differs from baked hydrology')
    if not level.save.save_map(world,level.village):raise RuntimeError('Cannot save final woodland')
    (batch/'forest.json').write_text(json.dumps(dict(pools=pools,water_actors=len(water_actors),shore_grass=shores,
                                                     fine_grass=count,grass_cells=cells),indent=2))

if __name__=='__main__':install()

