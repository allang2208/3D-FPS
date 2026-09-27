"""Import fitted Fab derivatives into new dungeon-only packages; preserve source packs."""
import unreal as u,json,re,importlib.util
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRuinEarthwork20260921')
spec=importlib.util.spec_from_file_location('dungeon_earthwork_materials',ROOT/'Scripts/earthwork_materials.py')
graphs=importlib.util.module_from_spec(spec);spec.loader.exec_module(graphs)
OUT='/Game/Dungeons/AtmosphereV2/RoomInteriors/Earthwork'
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'materials':{},'meshes':{},'source_maps_reused':True,'tests_run':False,'screenshots_taken':False}
receipt_path=ROOT/'Receipts/asset-import.json'

def write():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Required source unavailable '+path)
    return obj
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Gameplay active; keep current play intact')
for name,recipe in manifest['materials'].items():
    instance_path=OUT+'/Materials/MI_Earth_'+name
    instance=u.load_asset(instance_path)
    if not instance:
        if recipe.get('native_parent'):
            parent=load(recipe['native_parent'])
        else:
            material_path=OUT+'/Materials/M_Earth_'+name;parent=u.load_asset(material_path)
            if not parent:
                parent=A.create_asset('M_Earth_'+name,OUT+'/Materials',u.Material,u.MaterialFactoryNew())
                graphs.build_graph(parent,name,recipe,manifest['materials']);save(parent)
        instance=A.create_asset('MI_Earth_'+name,OUT+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(instance,parent)
    if recipe.get('tint'):L.set_material_instance_vector_parameter_value(instance,'Tint',u.LinearColor(*recipe['tint'],1))
    for key,value in recipe.get('scalar_overrides',{}).items():L.set_material_instance_scalar_parameter_value(instance,key,value)
    for key,value in recipe.get('vector_overrides',{}).items():L.set_material_instance_vector_parameter_value(instance,key,u.LinearColor(*value))
    L.update_material_instance(instance);save(instance)
    receipt['materials']['Earth_'+name]=instance.get_path_name();write()

for entry in manifest['objects']:
    path=OUT+'/Meshes/'+entry['name'];mesh=u.load_asset(path)
    if not mesh:
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=OUT+'/Meshes';task.destination_name=entry['name']
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opts;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=load(path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        if key not in receipt['materials']:raise RuntimeError('Unexpected fitted material slot '+key)
        mesh.set_material(i,load(receipt['materials'][key]))
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;mesh.set_editor_property('nanite_settings',settings)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh);receipt['meshes'][entry['name']]=mesh.get_path_name();write()
receipt['stage']='assets_saved';write()
print('EARTHWORK_ASSETS_SAVED',len(receipt['meshes']),len(receipt['materials']))
