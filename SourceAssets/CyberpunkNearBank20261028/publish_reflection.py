"""Manufacture the updated water reflection texture; no gameplay or acceptance render."""
from pathlib import Path
from datetime import datetime
import json,sys,unreal as u
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R));from design import *
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def main():
    report=json.loads((R/'installed.json').read_text())
    if report['stage']!='formal_map_saved':raise RuntimeError('Finish geometry publication first')
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    if not world:raise RuntimeError('Cannot load apartment')
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    prior=json.loads((PROJECT/'SourceAssets/CyberpunkUrbanLandscape20261025/installed.json').read_text())
    labels=set(prior['static_reflection_actors'])|set(report['actors'])|{'CITY_our_tower'}
    labels.update(n for n in actors if n.startswith('AP11_Tower_'))
    labels.update(n for n in actors if n.startswith('NBPCG_'))
    static=[actors[n] for n in sorted(labels) if n in actors]
    print('NEARBANK_REFLECTION_PRODUCTION',len(static),flush=True)
    cube=u.ApartmentExteriorAuthoringTools.bake_city_reflection(world,static,BASE+'/Textures/T_NB_CityReflection',u.Vector(1250,25000,-11125),2048)
    if not cube:raise RuntimeError('Static reflection manufacture failed')
    save(cube)
    water=actors['BAY_Water'];src=water.static_mesh_component.get_material(0)
    path=BASE+'/Materials/MI_NB_BayWater';mi=u.load_asset(path) if E.does_asset_exist(path) else A.duplicate_asset('MI_NB_BayWater',BASE+'/Materials',src)
    L.set_material_instance_texture_parameter_value(mi,'BayReflection',cube);L.update_material_instance(mi);save(mi)
    assets=json.loads((R/'assets_saved.json').read_text());assets['materials']['BayWater']=mi.get_path_name();assets['reflection_texture']=cube.get_path_name();(R/'assets_saved.json').write_text(json.dumps(assets,indent=2),encoding='utf8')
    water.modify();water.static_mesh_component.modify();water.static_mesh_component.set_material(0,mi)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Cannot save reflected apartment')
    report.update(reflection='updated_static_cube_saved',reflection_texture=cube.get_path_name(),reflection_face_resolution=2048,production_reflection_faces=6,water_material=mi.get_path_name(),saved_at=datetime.now().astimezone().isoformat())
    (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('NEARBANK_REFLECTION_AND_MAP_SAVED',flush=True)
if __name__=='__main__':main()
