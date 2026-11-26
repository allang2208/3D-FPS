"""Install talus sources into the existing rock layers of the official hill and road PCG themes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unreal as u

sys.path.insert(0,str(Path(__file__).resolve().parent))
import landscape_themes as themes


def install_sites(region,terrain,output=None,only=None):
    resources=themes.preset('HillsLandscape')['resources']
    if output is None:
        output=Path(os.environ.get('FPS_FOREST_TALUS_SOURCE',str(terrain.parent/resources['talus_source'])))
    catalog=terrain.parent/resources['talus_rock_catalog']
    python=os.environ.get('FPS_TERRAIN_PYTHON') or shutil.which('py')
    if not python:raise RuntimeError('Set FPS_TERRAIN_PYTHON to a Python interpreter with SciPy')
    cmd=[python]
    if Path(python).stem.lower()=='py':cmd.append('-3.11')
    cmd.extend(map(str,(Path(__file__).with_name('prepare_cliff_talus.py'),terrain,themes.source_root(),catalog,output)))
    env={k:v for k,v in os.environ.items() if k.upper() not in ('PYTHONHOME','PYTHONPATH')}
    if only is not None:cmd.extend(('--theme',only))
    subprocess.run(cmd,check=True,env=env)
    if only is not None:output=output/only/'Rocks'
    sites=json.loads((output/'talus.json').read_text(encoding='utf-8'))
    meshes=[u.load_asset(row['mesh']) for row in sites['meshes']]
    if not all(meshes) or not region.install_cliff_talus(str(output/'talus-sites.bin'),*meshes):
        raise RuntimeError('Could not install the slope-foot sites')
    return sites


def install(name=None):
    owners=[themes.preset(name)['id']] if name else ['HillsLandscape','RoadLandscape']
    import author_trail_cover_level as level
    world=level.save.load_map(level.village)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name('L_ForestPathVillage'):
        raise RuntimeError('Select the persistent forest village level')
    actors=level.actor_list()
    region=next(a for a in actors if isinstance(a,u.ForestVillageRegion) and a.get_path_name().startswith(level.village+'.'))
    terrain=level.src.parent/Path(themes.preset('HillsLandscape')['resources']['terrain_source']).parent
    sites=install_sites(region,terrain,level.src,owners[0] if name else None)
    templates=[c for a in actors if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name()
               for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
    if not templates:raise RuntimeError('Missing reference trees for theme bake')
    for owner in owners:
        if not region.bake_vegetation(themes.point_input(themes.preset(owner),None),templates,owner):
            raise RuntimeError('Could not bake '+owner)
    # Read the two independent rock point pages during authoring. Pin names also survive a single-theme rebuild.
    pins=('TalusFine','TalusFragment')
    counts={}
    for owner,stem in [('HillsLandscape','Ecology/DA_ForestRocks_'),('RoadLandscape','Themes/Road/DA_RoadRocks_')]:
        if owner not in owners:continue
        values=[0,0];page=1
        while True:
            path='/Game/ForestPathStudy/VillageRegion/'+stem+f'{page:02d}'
            if not u.EditorAssetLibrary.does_asset_exist(path):break
            data=u.load_asset(path).get_editor_property('data')
            for i,pin in enumerate(pins):
                arrays,_=data.get_typed_inputs_by_pin_label(pin,u.PCGBasePointData)
                values[i]+=sum(array.get_num_points() for array in arrays)
            page+=1
        if values!=sites['counts'][owner]:raise RuntimeError(f'{owner} rock pages {values} != {sites["counts"][owner]}')
        counts[owner]=values
    if not level.save.save_map(world,level.village):raise RuntimeError('Could not save the talus composition')
    (level.batch/'authored.json').write_text(json.dumps({'map':world.get_path_name(),'fans':sites.get('fans'),'points':counts,'meshes':sites['meshes']},indent=2))

if __name__=='__main__':install()
