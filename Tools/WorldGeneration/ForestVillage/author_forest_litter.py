"""Bake the latest forest-village dressing and road leaves without changing its terrain/water."""
import json,os,sys,subprocess,shutil
from pathlib import Path
import unreal as u
tools=Path(__file__).resolve().parent
sys.path.insert(0,str(tools))
import import_woodland_scans as scans
import author_roadside_leaves as leaves
import author_trail_cover_level as level
from forest_wood_retirement import retired_meshes

def install():
    src=level.src;batch=level.batch
    from landscape_themes import preset
    registered=Path(preset('丘陵景观')['resources']['terrain_source']).parent
    terrain=Path(os.environ.get('FPS_FOREST_DRESSING_TERRAIN',str(src.parent/registered)))
    if not (src/'wood-palette.json').is_file():scans.wood()
    retired=retired_meshes()
    palette=[row for row in json.loads((src/'wood-palette.json').read_text()) if row['mesh'] not in retired]
    for row in palette:
        mesh=u.load_asset(row['mesh'])
        if not mesh:raise RuntimeError('Missing imported scan '+row['mesh'])
        row['size_cm']=scans.rest_log(mesh,row['role'])
    (src/'wood-palette.json').write_text(json.dumps(palette,indent=2))
    python=os.environ.get('FPS_TERRAIN_PYTHON') or shutil.which('py')
    if not python:raise RuntimeError('Set FPS_TERRAIN_PYTHON to an interpreter with SciPy and Pillow')
    args=[python]+(['-3.11'] if Path(python).name.lower() in ('py','py.exe') else [])
    env={k:v for k,v in os.environ.items() if k not in ('PYTHONHOME','PYTHONPATH')}
    subprocess.run(args+[str(tools/'prepare_forest_litter.py'),str(src),str(terrain),str(src/'Dressing')],env=env,check=True)
    leaves.install(src)
    w=level.save.load_map(level.village)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name('L_ForestPathVillage'):raise RuntimeError('Wrong persistent level')
    actors=level.actor_list();region=next(a for a in actors if isinstance(a,u.ForestVillageRegion))
    templates=[c for a in actors if isinstance(a,u.PCGVolume) and '/L_ForestPathForest.' in a.get_path_name() for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
    if not templates or not region.bake_vegetation(str(src/'Dressing/planting.bin'),templates):raise RuntimeError('Forest PCG did not generate its saved points and pools')
    counts={x['mesh']:0 for x in palette};points={}
    for c in region.get_components_by_class(u.InstancedStaticMeshComponent):
        if c.static_mesh and c.static_mesh.get_path_name() in counts:
            path=c.static_mesh.get_path_name();count=c.get_instance_count();counts[path]+=count
            for i in range(count):
                t=c.get_instance_transform(i,True);p=u.MathLibrary.transform_location(t,c.static_mesh.get_bounds().origin)
                points.setdefault(path,[]).append([round(p.x*.01,2),round(p.y*.01,2)])
    if not all(counts.values()):raise RuntimeError('No accepted placement for '+str([p for p,n in counts.items() if not n]))
    if not level.save.save_map(w,level.village):raise RuntimeError('Could not save forest dressing level')
    (batch/'baked.json').write_text(json.dumps(dict(meshes=counts,total=sum(counts.values()),points_m=points),indent=2))

if __name__=='__main__':install()
