"""Update only the existing S12K resonance mesh and angled pose profile."""
import unreal as u
import json,shutil,hashlib
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KResonance20261019';E=u.EditorAssetLibrary
grip_path='/Game/Weapons/Saiga12K/Detail20261018/Attachments/SM_Saiga12K_angled'
profile_path='/Game/Weapons/Saiga12K/InspectClearance20261018/Profiles/DA_angled'
headless='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not headless and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
 raise RuntimeError('PIE_ACTIVE: preserve the running game; stop only with user authorization')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in (grip_path,profile_path)):raise RuntimeError('Target contains unsaved edits; preserve it')
fit=json.loads((O/'Authoring/fit.json').read_text());spec=json.loads((O/'Profiles/DA_angled.json').read_text());original=json.loads((O/'Inputs/profile.json').read_text())
mesh=u.load_asset(grip_path);profile=u.load_asset(profile_path)
def serialize(p):
 rows=[]
 for c in p.get_editor_property('clips'):
  base=c.get_editor_property('base');retained=c.get_editor_property('retained')
  rows.append({'base':base.get_path_name(),'duration':c.get_editor_property('duration'),'retained':retained.get_path_name() if retained else None,'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]})
 return {'family':str(p.get_editor_property('family')),'clips':rows}
if serialize(profile)!=original:raise RuntimeError('Profile changed since authoring; preserve concurrent edit')
for path in (grip_path,profile_path):
 source=P/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=O/'Before/Content'/(path.removeprefix('/Game/')+'.uasset')
 backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(source,backup)
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;LS=u.GeometryScript_List;ED=u.GeometryScript_MeshEdits;MT=u.GeometryScript_Materials
dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read mesh')
_,vp,_=Q.get_all_vertex_positions(dm,False);vp=[[v.x,v.y,v.z] for v in LS.convert_vector_list_to_array(vp)]
source=json.loads((O/'Inputs/grip.json').read_text())
if vp!=source['positions']:raise RuntimeError('Grip changed since authoring; preserve concurrent edit')
ids=next(v for v in Q.get_all_triangle_i_ds(dm) if isinstance(v,u.GeometryScriptIndexList))
remove=[i for i in LS.convert_index_list_to_array(ids) if MT.get_triangle_material_id(dm,i)[0]==1]
ED.delete_triangles_from_mesh(dm,LS.convert_array_to_index_list(remove),True)
u.GeometryScript_MeshTransforms.transform_mesh(dm,u.Transform(location=u.Vector(*fit['offset_root_cm'])))
s=fit['saddle'];flat=[s['positions'][v] for t in s['triangles'] for v in t]
_,vi=ED.add_vertices_to_mesh(dm,LS.convert_array_to_vector_list([u.Vector(*v) for v in flat]),True);vi=list(LS.convert_index_list_to_array(vi))
_,ti=ED.add_triangles_to_mesh(dm,LS.convert_array_to_triangle_list([u.IntVector(*vi[i:i+3]) for i in range(0,len(vi),3)]),0,True)
for fi,tid in enumerate(LS.convert_index_list_to_array(ti)):
 MT.set_triangle_material_id(dm,tid,1,True);n=u.Vector(*s['normals'][fi]);u.GeometryScript_Normals.set_mesh_triangle_normals(dm,tid,u.GeometryScriptTriangle(vector0=n,vector1=n,vector2=n),True)
 uv=[u.Vector2D(*v) for v in s['uv'][fi]]
 for channel in range(Q.get_num_uv_sets(dm)):
  u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm,channel,tid,u.GeometryScriptUVTriangle(uv0=uv[0],uv1=uv[1],uv2=uv[2]),True)
_,status=G.copy_mesh_to_static_mesh(dm,mesh,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write resonance mesh')
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
# Rebuild the existing distance LODs from the corrected source. Both views use
# this same mesh, so no donor-coordinate LOD can reappear at distance.
options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False
options.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=r,screen_size=z) for r,z in ((1.,1.),(.5,.18),(.25,.075))]
SM.set_lods(mesh,options)
u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
E.set_metadata_tag(mesh,'Saiga12KResonanceFit','20261019: lowered 2.1497 cm; closed saddle fitted to actual handguard underside')
if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed')
receipt={'complete':False,'saved':[grip_path],'offset_root_cm':fit['offset_root_cm'],'runtime_tested':False}
(O/'Receipts/saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
if not profile.set_shared_clips_from_json(json.dumps(spec)):raise RuntimeError('Profile import failed')
E.set_metadata_tag(profile,'Saiga12KResonanceFit','20261019: native support chain follows fitted resonance grip; fingers and magazine/bolt contacts retained')
if not E.save_loaded_asset(profile,False):raise RuntimeError('Profile save failed')
receipt['saved'].append(profile_path);receipt['complete']=True;receipt['clips']=len(spec['clips']);receipt['lods']=SM.get_lod_count(mesh)
(O/'Receipts/saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps(receipt))
