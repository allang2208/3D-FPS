"""Use the user-approved M4 stock verbatim, with M16's existing closed receiver adapter."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
SOURCE='/Game/Weapons/TacticalTelescopicStock20260914/M4/SM_TacticalTelescopicStock'
TARGET='/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_tactical_telescopic'
R={'selected_donor':'M4','selection_authority':'User confirmed M4 in this chat on 2026-10-15','saved':False,'gameplay_tested':False}
RP=O/'install_receipt.json'
if RP.exists():raise RuntimeError('Preserve the existing installation receipt; do not repeat the replacement')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE: stop current play before the stock mesh replacement')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in (SOURCE,TARGET)):raise RuntimeError('The selected source or destination has unsaved changes')
def disk(p):return P/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(disk(p).read_bytes()).hexdigest()
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def record():RP.write_text(json.dumps(R,indent=2),encoding='utf-8')
source=u.load_asset(SOURCE);target=u.load_asset(TARGET)
if not source or not target:raise RuntimeError('Missing selected stock')
R.update(source=SOURCE,target=TARGET,source_sha256=sha(SOURCE),before_sha256=sha(TARGET))
before=O/'Before/SM_M16_tactical_telescopic.uasset';before.parent.mkdir(exist_ok=True)
if before.exists() and hashlib.sha256(before.read_bytes()).hexdigest()!=R['before_sha256']:raise RuntimeError('Captured M16 baseline changed')
if not before.exists():shutil.copy2(disk(TARGET),before)
lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL)
opts=u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True)
donor,status=G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),opts,lod)
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read approved M4 source')
adapter,status=G.copy_mesh_from_static_mesh(target,u.DynamicMesh(),opts,lod)
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read M16 receiver interface')
source_mats,source_indices,source_names,status=G.get_section_material_list_from_static_mesh(source,lod)
target_mats,target_indices,target_names,status=G.get_section_material_list_from_static_mesh(target,lod)
interface=next(i for i,n in enumerate(target_names) if str(n)=='M16_InterfaceMetal')
_,tt,_=Q.get_all_triangle_indices(adapter,False);target_tri=u.GeometryScript_List.convert_triangle_list_to_array(tt)
retained=[];deleted=[]
for i in range(len(target_tri)):
 mid=u.GeometryScript_Materials.get_triangle_material_id(adapter,i)[0]
 (retained if mid==interface else deleted).append(i)
if len(retained)!=1268:raise RuntimeError('M16 interface changed; preserve current mesh')
u.GeometryScript_MeshEdits.delete_triangles_from_mesh(adapter,u.GeometryScript_List.convert_array_to_index_list(deleted),True)
for i in retained:u.GeometryScript_Materials.set_triangle_material_id(adapter,i,0,True)
_,dt,_=Q.get_all_triangle_indices(donor,False);donor_tri=u.GeometryScript_List.convert_triangle_list_to_array(dt)
for i in range(len(donor_tri)):
 mid=u.GeometryScript_Materials.get_triangle_material_id(donor,i)[0]
 u.GeometryScript_Materials.set_triangle_material_id(donor,i,mid+1,True)
# Authored M4 -> M16 root transform, in UE centimeters. No scaling or surface edits.
# M16: (M4.y - .0038, -M4.x - 4.1045, M4.z + 9.17).
transform=u.Transform(location=u.Vector(-.0038,-4.1045,9.17),rotation=u.Rotator(pitch=0,yaw=-90,roll=0),scale=u.Vector(1,1,1))
u.GeometryScript_MeshTransforms.transform_mesh(donor,transform)
u.GeometryScript_MeshEdits.append_mesh(donor,adapter,u.Transform(),False,u.GeometryScriptAppendMeshOptions())
materials=[target_mats[interface]]+list(source_mats);names=[u.Name('M16_InterfaceMetal')]+list(source_names)
write=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,use_original_vertex_order=False,replace_materials=True,new_materials=materials,new_material_slot_names=names)
_,status=G.copy_mesh_to_static_mesh(donor,target,write,u.GeometryScriptMeshWriteLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write M16 stock')
u.ASH12AttachmentAssetTools.disable_runtime_fast_build(target)
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
settings=sms.get_lod_build_settings(source,0);settings.recompute_normals=False;settings.recompute_tangents=False
sms.set_lod_build_settings(target,0,settings)
E.set_metadata_tag(target,'M16StockDonor','M4 user-approved stock 20261015: complete body, exact UVs/normals/tangents/materials; M16 closed receiver interface retained')
save(target)
R.update(saved=True,sha256=sha(TARGET),donor_triangles=len(donor_tri),retained_interface_triangles=len(retained),materials={str(n):m.get_path_name() for n,m in zip(names,materials)},transform={'yaw_degrees':-90,'translation_cm':[-.0038,-4.1045,9.17],'scale':1},surface_rebaked=False,donor_modified=False);record()
final=O/'Final';final.mkdir(exist_ok=True)
task=u.AssetExportTask();task.object=target;task.filename=str(final/'SM_M16_tactical_telescopic.fbx');task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Final export failed')
target.get_editor_property('asset_import_data').scripted_add_filename(task.filename,0,'');save(target)
R.update(export=task.filename,sha256=sha(TARGET));record()
# Keep this exact donor material recipe when older M16 source scripts reimport this mesh.
manifest=P/'SourceAssets/WeaponSurface20260930/M16/current_surface_bindings.json'
backup=O/'Before/current_surface_bindings.json'
if not backup.exists():shutil.copy2(manifest,backup)
data=json.loads(manifest.read_text(encoding='utf-8'));data['meshes'][target.get_path_name()]=R['materials']
manifest.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
R.update(binding_manifest=str(manifest),complete=True);record()
print('M16_M4_STOCK_DONOR_SAVED',TARGET,'body=',len(donor_tri),'M16_interface=',len(retained),flush=True)
