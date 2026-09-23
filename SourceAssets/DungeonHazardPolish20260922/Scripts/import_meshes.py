import unreal as u,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/HazardPolish20260922'
ROOMS=ROOT.parent/'DungeonRoomShells20260922'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
items=[dict(name='SM_DungeonPusChannel',fbx=str(ROOT/'Authored/SM_DungeonPusChannel.fbx'),destination=BASE+'/Meshes',materials={'DP_Pus':BASE+'/Materials/MI_DungeonViscousPus'},collision=False)]
for obj in json.loads((ROOMS/'Authored/manifest.json').read_text())['objects']:
    if obj['room']=='ShoredBreach' and obj['kind'] in ('Shell','Debris'):
        obj['destination']='/Game/Dungeons/RoomShells20260922/Meshes';items.append(obj)
receipt={'meshes':{},'tests_run':False}
for item in items:
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=item['destination'];task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
    options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('Import failed '+item['name'])
    mesh=u.load_asset(item['destination']+'/'+item['name'])
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][name])
        if not material:raise RuntimeError('Required material missing '+item['materials'][name])
        mesh.set_material(index,material)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if item['name']=='SM_DungeonPusChannel':
        mesh.set_editor_property('positive_bounds_extension',u.Vector(0,0,2))
        mesh.set_editor_property('negative_bounds_extension',u.Vector(0,0,2))
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+mesh.get_path_name())
    receipt['meshes'][item['name']]=mesh.get_path_name()
    (ROOT/'Receipts/meshes.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt['stage']='meshes_saved';(ROOT/'Receipts/meshes.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('HAZARD_AND_FRACTURE_MESHES_SAVED',len(items))
