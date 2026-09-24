"""Reimport scoped repaired exports, preserving slot identities, full geometry and gameplay collision."""
import hashlib,json,re,shutil,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active PIE')
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_mesh_material_usage
source=json.loads((ROOT/'Receipts/geometry.json').read_text())
if source['stage']!='authored':raise RuntimeError('Geometry production incomplete')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt_path=ROOT/'Receipts/import.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(stage='importing',meshes={},runtime_tested=False)
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
count=0
for path,item in source['meshes'].items():
    source_hash=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    if path in receipt['meshes'] and receipt['meshes'][path].get('source_file_sha256')==source_hash:continue
    if path in dirty:raise RuntimeError('Preserve unsaved target '+path)
    mesh=u.load_asset(path)
    if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Missing active mesh '+path)
    previous=mesh.get_editor_property('nanite_settings').copy()
    collision=mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')
    bindings={str(s.material_slot_name):s.material_interface for s in mesh.get_editor_property('static_materials')}
    # FBX round trips may add numeric suffixes; do not bind materials by slot index.
    canonical={re.sub(r'[._][0-9]{3}$','',name):mat for name,mat in bindings.items()}
    relative=Path(path.removeprefix('/Game/')+'.uasset');original=PROJECT/'Content'/relative;backup=ROOT/'Sources/Before/Content'/relative
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,backup)
    before_triangles=mesh.get_num_triangles(0)
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1]
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh or not task.get_objects():raise RuntimeError('Reimport failed '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=str(slot.material_slot_name);key=re.sub(r'[._][0-9]{3}$','',name)
        material=bindings.get(name) or canonical.get(key)
        if not material:raise RuntimeError('Unresolved original slot '+path+' '+name)
        mesh.set_material(i,material)
    ensure_mesh_material_usage(mesh)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',collision)
    previous.explicit_tangents=True
    mesh.set_editor_property('nanite_settings',previous)
    if previous.enabled and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
    receipt['meshes'][path]=dict(source_file_sha256=source_hash,operation=item['operation'],triangles_before=before_triangles,triangles_after=mesh.get_num_triangles(0),
        material_slots={k:v.get_path_name() for k,v in bindings.items() if v},collision=str(collision),saved=True)
    count+=1;receipt_path.write_text(json.dumps(receipt,indent=2));print('SURFACE_REIMPORT_SAVED',len(receipt['meshes']),len(source['meshes']),path,flush=True)
    # Keep distance-field/Nanite work bounded and release meshes between batches.
    if count>=8:break
    mesh=None;u.collect_garbage()
receipt['remaining']=sum(receipt['meshes'].get(path,{}).get('source_file_sha256')!=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    for path,item in source['meshes'].items())
receipt['stage']='meshes_saved' if receipt['remaining']==0 else 'next_batch'
receipt_path.write_text(json.dumps(receipt,indent=2));print('SURFACE_REIMPORT_BATCH',receipt['stage'],len(receipt['meshes']),flush=True)
