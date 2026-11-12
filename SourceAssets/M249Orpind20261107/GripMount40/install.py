"""Publish only this grip fit. Preserve approved materials, bones and pose assets."""
from pathlib import Path
import gzip
import json
import sys
import zipfile
import unreal as ue

sys.path.insert(0,str(Path(__file__).resolve().parent))
from assets import HERE,PROJECT,FRONT,BACK,TABLE,POSES,RIG,disk,digest

fit=json.loads((HERE/'fit.json').read_text())
expected=json.loads((HERE/'inputs.json').read_text())
receipt=HERE/'saved.json'
saved=json.loads(receipt.read_text()) if receipt.exists() else {}
dirty={p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path,h in expected.items():
    if path in dirty or digest(path)!=saved.get(path,h):raise RuntimeError('Changed production input '+path)
backup=HERE/'before.zip'
if not backup.exists():
    with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as out:
        for p in expected:out.write(disk(p),str(disk(p).relative_to(PROJECT)))

def save(path,asset):
    if not ue.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+path)
    saved[path]=digest(path)
    receipt.write_text(json.dumps(saved,indent=2))
    print('M249_GRIP_MOUNT_SAVED',path,flush=True)

def translate(path,delta):
    mesh=ue.load_asset(path)
    if mesh.get_num_lods()!=1:raise RuntimeError('Unexpected authored LOD count '+path)
    dm,out=ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,ue.DynamicMesh(),ue.GeometryScriptCopyMeshFromAssetOptions(),ue.GeometryScriptMeshReadLOD())
    if out!=ue.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read '+path)
    ue.GeometryScript_MeshTransforms.translate_mesh(dm,ue.Vector(*delta))
    opt=ue.GeometryScriptCopyMeshToAssetOptions();opt.set_editor_property('use_original_vertex_order',True)
    _,out=ue.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,mesh,opt,ue.GeometryScriptMeshWriteLOD())
    if out!=ue.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Translate '+path)
    save(path,mesh)

def slots(asset):
    return {key:slot.material_interface for slot in asset.static_materials for key in
            (str(slot.material_slot_name),str(slot.get_editor_property('imported_material_slot_name'))) if slot.material_interface}

def import_part(path):
    dest,name=path.rsplit('/',1)
    mesh=ue.load_asset(path);materials=slots(mesh)
    task=ue.AssetImportTask();task.filename=str(HERE/'Exports'/(name+'.fbx'))
    task.destination_name=name;task.destination_path=dest;task.automated=True;task.replace_existing=True;task.save=False
    opt=ue.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
    opt.mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH;opt.automated_import_should_detect_type=False
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.generate_lightmap_u_vs=False
    opt.static_mesh_import_data.normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task.options=opt
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('No FBX import '+path)
    mesh=ue.load_asset(path);mats=list(mesh.static_materials)
    for i,s in enumerate(mats):
        mat=materials.get(str(s.get_editor_property('imported_material_slot_name'))) or materials.get(str(s.material_slot_name))
        if not mat and len(set(materials.values()))==1:mat=next(iter(materials.values()))
        if not mat:raise RuntimeError('Cannot bind original surface '+path+' '+str(s.material_slot_name))
        s.material_interface=mat;mats[i]=s
    mesh.set_editor_property('static_materials',mats)
    ue.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
    save(path,mesh)

if RIG not in saved:
    rig=ue.load_asset(RIG)
    centers=[ue.Vector(*v) for v in fit['component_centers']]
    if not ue.M24ChassisAssetTools.move_factory_faces(rig,'M249_Factory_Receiver','M249_Factory_RearGrip',centers):
        raise RuntimeError('Unable to repartition the receiver')
    save(RIG,rig)

cv='Interchange.FeatureFlags.Import.FBX'
previous=ue.SystemLibrary.get_console_variable_int_value(cv)
ue.SystemLibrary.execute_console_command(None,cv+' 0')
try:
    for path in [*BACK.values(),*TABLE.values()]:
        if path not in saved:import_part(path)
finally:ue.SystemLibrary.execute_console_command(None,cv+' '+str(previous))

for key,path in FRONT.items():
    if path not in saved:translate(path,fit['front_deltas_root_cm'][key])
for family,path in POSES.items():
    if path in saved:continue
    profile=ue.load_asset(path)
    if not profile.set_shared_clips_from_json(gzip.decompress((HERE/(family+'.json.gz')).read_bytes()).decode()):
        raise RuntimeError('Grip pose '+family)
    save(path,profile)
print('M249_GRIP_MOUNT_PUBLISHED',len(saved),flush=True)
