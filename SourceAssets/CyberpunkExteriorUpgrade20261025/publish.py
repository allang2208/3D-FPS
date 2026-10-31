"""Save the formal replacement and manufacture its static water-reflection texture."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil,hashlib
R=Path(__file__).resolve().parent;PROJECT=R.parents[1];BASE='/Game/Props/CyberpunkExteriorUpgrade20261025';MAP='/Game/GameMaps/L_CyberpunkApartment'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
def duplicate(source,name):
    path=BASE+'/Materials/'+name
    return u.load_asset(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',source)

def main():
    if not hasattr(u,'ApartmentExteriorAuthoringTools'):raise RuntimeError('Build the native exterior authoring module first')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve active gameplay')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    existing=json.loads((R/'assets_saved.json').read_text())
    uvrepair=R/'landmark_uv_repair.json'
    if any(f'Landmark_{i}' not in existing['meshes'] for i in range(5)) or (uvrepair.exists() and json.loads(uvrepair.read_text()).get('stage')=='source_repaired'):
        runpy.run_path(str(R/'save_refined_geometry.py'))
    disk=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')/disk.name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    report=runpy.run_path(str(R/'install_level.py'))['apply_upgrade'](world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Exterior map save failed')
    report.update(stage='formal_map_saved',saved_at=datetime.now().astimezone().isoformat(),backup=str(backup),interactive_editor_started=False)
    (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('EXTERIOR_GEOMETRY_MAP_SAVED',len(report['buildings']),flush=True)

    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    static=[]
    for label,a in actors.items():
        include=label.startswith(('EX25_','BAY_City_','AP7_BayLandmark_','AP18_Frontage_','AP18_Lookouts_','AP18_Terminal_')) or label in ('BAY_FarCity','BAY_FarHeadland','BAY_Harbor','AP16_Roads','AP16_Trees','AP16_StreetFurniture','AP16_Junctions','AP18_MooredFerries')
        if label.startswith('UL25_') and not a.actor_has_tag('UrbanWater'):include=True
        if include:static.append(a)
    cube=u.ApartmentExteriorAuthoringTools.bake_city_reflection(world,static,BASE+'/Textures/T_Exterior_CityReflection',u.Vector(1250,25000,-11125),2048)
    if not cube:raise RuntimeError('Native production reflection bake failed; geometry remains saved')
    save(cube)
    # Derive from the live clock-aware water surface, retaining every dynamic branch.
    water=actors['BAY_Water'];source=water.static_mesh_component.get_material(0);parent=source
    while isinstance(parent,u.MaterialInstanceConstant):parent=parent.get_editor_property('parent')
    master=duplicate(parent,'M_Exterior_Water');mapping=0;samplers=0
    for n in L.get_material_expressions(master):
        if isinstance(n,u.MaterialExpressionCustom):
            code=n.get_editor_property('code')
            if 'return float3(-r.x,r.z,r.y);' in code:
                n.set_editor_property('code',code.replace('return float3(-r.x,r.z,r.y);','return r;'));n.set_editor_property('description','Native UE city cube direction');mapping+=1
            elif str(n.get_editor_property('description'))=='Native UE city cube direction':mapping+=1
        if isinstance(n,u.MaterialExpressionTextureSampleParameterCube) and str(n.get_editor_property('parameter_name'))=='BayReflection':n.set_editor_property('texture',cube);samplers+=1
    if mapping!=1 or samplers!=1:raise RuntimeError('Current water cube binding requires a different adapter')
    errors=L.recompile_material(master)
    if errors:raise RuntimeError('Water material compilation '+str(errors))
    save(master);instance=duplicate(source,'MI_Exterior_Water');L.set_material_instance_parent(instance,master);L.set_material_instance_texture_parameter_value(instance,'BayReflection',cube);L.update_material_instance(instance);save(instance)
    assets=json.loads((R/'assets_saved.json').read_text());assets['materials']['Water']=instance.get_path_name();assets['materials']['WaterMaster']=master.get_path_name();assets['reflection_texture']=cube.get_path_name();(R/'assets_saved.json').write_text(json.dumps(assets,indent=2),encoding='utf8')
    water.modify();water.static_mesh_component.modify();water.static_mesh_component.set_material(0,instance)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Final reflected city save failed')
    report.update(reflection='native_cube_saved',reflection_texture=cube.get_path_name(),static_reflection_actors=[a.get_actor_label() for a in static],saved_at=datetime.now().astimezone().isoformat(),map_sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),production_reflection_faces=6,reflection_face_resolution=2048)
    (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    urban=PROJECT/'SourceAssets/CyberpunkUrbanLandscape20261025'
    if (urban/'installed.json').exists():
        ua=json.loads((urban/'assets_saved.json').read_text(encoding='utf8'));ua['materials']['BayWater']=instance.get_path_name();ua['materials']['BayWaterMaster']=master.get_path_name();ua['reflection_texture']=cube.get_path_name();(urban/'assets_saved.json').write_text(json.dumps(ua,indent=2),encoding='utf8')
        ur=json.loads((urban/'installed.json').read_text(encoding='utf8'));ur.update(reflection_texture=cube.get_path_name(),saved_at=report['saved_at']);(urban/'installed.json').write_text(json.dumps(ur,indent=2),encoding='utf8')
    print('EXTERIOR_FORMAL_MAP_AND_REFLECTION_SAVED',len(report['buildings']),len(report['roof_services']),flush=True)
if __name__=='__main__':main()
