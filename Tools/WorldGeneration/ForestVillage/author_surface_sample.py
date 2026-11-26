"""Apply the approved R3 pilot to the existing map with a headless editor commandlet."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess

import unreal as u

MAP='/Game/GameMaps/L_ForestPathVillage'
SAMPLE='/Game/ForestPathStudy/VillageRegion/SurfaceSample'
ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
TOOLS=ROOT/'Tools/WorldGeneration/ForestVillage'


def apply(region,templates,baseline,source,batch):
    env=dict(os.environ)
    for key in ('PYTHONHOME','PYTHONPATH'):
        env.pop(key,None)
    with (batch/'sample-generator.log').open('w',encoding='utf8') as log:
        subprocess.run([os.environ['FPS_REGION_PYTHON'],'-I',str(TOOLS/'generate_surface_sample.py'),
                        str(baseline),str(source)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    core,edge,gate=runpy.run_path(str(TOOLS/'author_sample_materials.py'))['build'](source)
    (ROOT/'Content/ForestPathStudy/VillageRegion/SurfaceSample/Terrain').mkdir(parents=True,exist_ok=True)
    if not region.apply_surface_sample(str(source),core,edge,gate):
        raise RuntimeError('Could not update the four sample tiles and gate apron')
    slope = runpy.run_path(str(TOOLS/'author_slope_grass.py'))
    scene = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    slope_dir = source/'HillsSlopeGrass'
    verge = Path(os.environ.get('FPS_WILD_GRASS_SOURCE',baseline.parent/'WildGrass-oilox20'))
    slope['apply'](region,templates,scene,source,slope_dir,os.environ['FPS_REGION_PYTHON'],verge)
    info = json.loads((source/'generation.json').read_text())
    info['hillside_grass'] = json.loads((slope_dir/'generation.json').read_text())
    return info


def main():
    batch=Path(os.environ['FPS_FOREST_VILLAGE_BATCH'])
    source=Path(os.environ['FPS_FOREST_REGION_SOURCE'])
    baseline=Path(os.environ['FPS_FOREST_REGION_BASELINE'])
    file=ROOT/'Content/GameMaps/L_ForestPathVillage.umap'
    previous=hashlib.sha256(file.read_bytes()).hexdigest()
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    region=next(a for a in actors if isinstance(a,u.ForestVillageRegion) and a.get_path_name().startswith(MAP+'.'))
    templates=[c for a in actors if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name()
               for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
    info=apply(region,templates,baseline,source,batch)
    if hashlib.sha256(file.read_bytes()).hexdigest()!=previous:
        raise RuntimeError('Persistent map changed during the bake')
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):
        raise RuntimeError('Could not publish the forest village')
    info.update(map=MAP,previous_sha256=previous,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                materials=SAMPLE,graph='/Game/ForestPathStudy/VillageRegion/PCG_ForestVillageSurroundings',
                source=str(source))
    (batch/'published.json').write_text(json.dumps(info,indent=2),encoding='utf8')
    u.log('FOREST_SURFACE_GRASS_SAVED '+json.dumps(info))


if __name__=='__main__':
    main()
