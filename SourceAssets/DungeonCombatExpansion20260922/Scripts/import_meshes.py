"""Import current authored meshes to the new revision, leaving old assets recoverable."""
import unreal as u,json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ROOMS=ROOT.parent/'DungeonRoomShells20260922';BASE='/Game/Dungeons/CombatExpansion20260922'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
items=json.loads((ROOMS/'Authored/manifest.json').read_text())['objects']+json.loads((ROOT/'Authored/fluids.json').read_text())['objects']
receiptfile=ROOT/'Receipts/meshes.json';receipt=json.loads(receiptfile.read_text()) if receiptfile.exists() else {'stage':'importing','meshes':{},'hashes':{},'tests_run':False}
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('End play before dungeon integration')
for item in items:
    digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest();path=BASE+'/Meshes/'+item['name']
    if receipt['hashes'].get(item['name'])==digest and E.does_asset_exist(path):continue
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name'];task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(item['materials'][key])
        if not mat:raise RuntimeError('Missing material '+key)
        mesh.set_material(i,mat)
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;mesh.set_editor_property('nanite_settings',ns)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if 'Pus' in item['name']:
        mesh.set_editor_property('positive_bounds_extension',u.Vector(20,5,6));mesh.set_editor_property('negative_bounds_extension',u.Vector(5,5,85 if 'Drops' in item['name'] else 5))
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save '+path)
    receipt['meshes'][item['name']]=path;receipt['hashes'][item['name']]=digest;receiptfile.write_text(json.dumps(receipt,indent=2))
receipt['stage']='meshes_saved';receiptfile.write_text(json.dumps(receipt,indent=2))
# The standard room installer consumes this path mapping on future generation.
(ROOMS/'Receipts/import.json').write_text(json.dumps(dict(stage='meshes_saved',meshes={i['name']:receipt['meshes'][i['name']] for i in items if i['name'].startswith('SM_RS_')},tests_run=False),indent=2))
print('COMBAT_ROOM_MESHES_SAVED',len(receipt['meshes']))
