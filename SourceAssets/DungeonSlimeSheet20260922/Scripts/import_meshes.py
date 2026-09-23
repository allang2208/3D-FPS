"""Only five tile layers and two pipe-fluid meshes; room layout is unchanged."""
import unreal as u,json,re,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ROOMS=ROOT.parent/'DungeonRoomShells20260922';BASE='/Game/Dungeons/SlimeSheet20260922'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
items=[r for r in json.loads((ROOMS/'Authored/manifest.json').read_text())['objects'] if r['kind']=='Tiles']+json.loads((ROOT/'Authored/fluids.json').read_text())['objects']
if os.environ.get('DUNGEON_SLIME_FLUID_ONLY')=='1':items=[i for i in items if 'Pus' in i['name']]
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('End play before importing the updated dungeon meshes')
receipt=json.loads((ROOT/'Receipts/meshes.json').read_text()) if os.environ.get('DUNGEON_SLIME_FLUID_ONLY')=='1' else {'meshes':{},'tests_run':False}
for item in items:
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name'];task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);path=BASE+'/Meshes/'+item['name'];mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mesh.set_material(i,u.load_asset(item['materials'][key]))
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;mesh.set_editor_property('nanite_settings',ns)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if 'Pus' in item['name']:
        mesh.set_editor_property('positive_bounds_extension',u.Vector(15,3,3));mesh.set_editor_property('negative_bounds_extension',u.Vector(3,3,85 if 'Drops' in item['name'] else 4))
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
    receipt['meshes'][item['name']]=path
mapping=json.loads((ROOMS/'Receipts/import.json').read_text());mapping['meshes'].update({k:v for k,v in receipt['meshes'].items() if k.startswith('SM_RS_')});(ROOMS/'Receipts/import.json').write_text(json.dumps(mapping,indent=2))
receipt['stage']='meshes_saved';(ROOT/'Receipts/meshes.json').write_text(json.dumps(receipt,indent=2));print('CONVERGING_SLIME_TILE_MESHES_SAVED',len(items))
