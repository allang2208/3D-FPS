import unreal, json
from pathlib import Path
out = Path(unreal.Paths.project_saved_dir()) / 'StormClouds'
out.mkdir(exist_ok=True)
rows = []
def material(m):
    if not m: return None
    row = {'path':m.get_path_name(), 'scalar':{}, 'vector':{}}
    lib = unreal.MaterialEditingLibrary
    for name in lib.get_scalar_parameter_names(m):
        row['scalar'][str(name)] = lib.get_material_default_scalar_parameter_value(m,name) if isinstance(m,unreal.Material) else lib.get_material_instance_scalar_parameter_value(m,name)
    for name in lib.get_vector_parameter_names(m):
        row['vector'][str(name)] = str(lib.get_material_default_vector_parameter_value(m,name) if isinstance(m,unreal.Material) else lib.get_material_instance_vector_parameter_value(m,name))
    return row
cls=unreal.load_class(None,'/Game/Lighting/BP_FPS_DayNightManager.BP_FPS_DayNightManager_C')
cdo=unreal.get_default_object(cls)
props={}
for n in dir(cdo):
    if any(s in n.lower() for s in ['cloud','sun','sky','light','weather']):
        try: props[n]=str(cdo.get_editor_property(n))
        except: pass
rows.append({'blueprint':props})
editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for name in ['L_Normandy_FPS_Test','L_MilitaryTrench_FPS_Test']:
    editor.load_level('/Game/GameMaps/'+name)
    for a in actors.get_all_level_actors():
        for c in a.get_components_by_class(unreal.VolumetricCloudComponent):
            rows.append({'map':name,'actor':a.get_actor_label(),'material':material(c.get_editor_property('material'))})
for path in unreal.EditorAssetLibrary.list_assets('/Game/PWL_Light_Manager',recursive=True):
    if 'cloud' in path.lower() and any(s in path.split('/')[-1] for s in ['M_','MI_']):
        a=unreal.load_asset(path)
        if isinstance(a,unreal.MaterialInterface): rows.append({'pwl':material(a)})
(out/'inspection.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
unreal.log('STORM_INSPECTION_OK')
