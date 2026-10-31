"""Save the landscaped formal map and manufacture the updated static city reflection."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy
R=Path(__file__).resolve().parent;BASE='/Game/Props/CyberpunkUrbanLandscape20261025';MAP='/Game/GameMaps/L_CyberpunkApartment'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def duplicate(src,name):
    p=BASE+'/Materials/'+name;return u.load_asset(p) if E.does_asset_exist(p) else A.duplicate_asset(name,BASE+'/Materials',src)
def main():
    runpy.run_path(str(R/'install_level.py'),run_name='__main__')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if not world:world=u.load_asset(MAP)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    static=[]
    for label,a in actors.items():
        include=label.startswith(('EX25_','BAY_City_','AP7_BayLandmark_','AP18_Frontage_','AP18_Lookouts_','AP18_Terminal_')) or label in ('BAY_FarCity','BAY_FarHeadland','BAY_FarTerrain','BAY_Harbor','AP16_Roads','AP16_Trees','AP16_StreetFurniture','AP16_Junctions','AP18_MooredFerries')
        if label.startswith('UL25_') and not a.actor_has_tag('UrbanWater'):include=True
        if include:static.append(a)
    print('URBAN_REFLECTION_PRODUCTION_BEGIN',len(static),flush=True)
    cube=u.ApartmentExteriorAuthoringTools.bake_city_reflection(world,static,BASE+'/Textures/T_UL_CityReflection',u.Vector(1250,25000,-11125),2048)
    if not cube:raise RuntimeError('Native reflection production incomplete; formal geometry already saved')
    save(cube)
    water=actors['BAY_Water'];src=water.static_mesh_component.get_material(0);parent=src
    while isinstance(parent,u.MaterialInstanceConstant):parent=parent.get_editor_property('parent')
    master=duplicate(parent,'M_UL_BayWater');count=0
    for n in L.get_material_expressions(master):
        if isinstance(n,u.MaterialExpressionTextureSampleParameterCube) and str(n.get_editor_property('parameter_name'))=='BayReflection':n.set_editor_property('texture',cube);count+=1
        if isinstance(n,u.MaterialExpressionCustom):
            code=n.get_editor_property('code')
            if 'return float3(-r.x,r.z,r.y);' in code:n.set_editor_property('code',code.replace('return float3(-r.x,r.z,r.y);','return r;'))
    if count!=1:raise RuntimeError('Water reflection adapter changed')
    errors=L.recompile_material(master)
    if errors:raise RuntimeError('Water shader compilation '+str(errors))
    save(master);mi=duplicate(src,'MI_UL_BayWater');L.set_material_instance_parent(mi,master);L.set_material_instance_texture_parameter_value(mi,'BayReflection',cube);L.update_material_instance(mi);save(mi)
    assets=json.loads((R/'assets_saved.json').read_text(encoding='utf8'));assets['materials']['BayWater']=mi.get_path_name();assets['materials']['BayWaterMaster']=master.get_path_name();assets['reflection_texture']=cube.get_path_name();(R/'assets_saved.json').write_text(json.dumps(assets,indent=2),encoding='utf8')
    water.modify();water.static_mesh_component.modify();water.static_mesh_component.set_material(0,mi)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Cannot save reflected formal map')
    report=json.loads((R/'installed.json').read_text(encoding='utf8'));report.update(reflection='native_cube_saved',reflection_texture=cube.get_path_name(),reflection_face_resolution=2048,production_reflection_faces=6,static_reflection_actors=[a.get_actor_label() for a in static],saved_at=datetime.now().astimezone().isoformat());(R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('URBAN_FORMAL_MAP_AND_REFLECTION_SAVED',report['counts'],flush=True)
if __name__=='__main__':main()
