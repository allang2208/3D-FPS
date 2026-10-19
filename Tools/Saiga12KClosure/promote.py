"""Update the existing runtime paths only after inspecting real UE captures."""
import unreal as u,json,shutil,sys,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KClosure20261018';D='/Game/Weapons/Saiga12K/Closure20261018';ACTIVE='/Game/Weapons/Saiga12K/Detail20261018'
for name in ('UE_Before.json','UE_After.json'):
 if not json.loads((O/'Preview'/name).read_text())['complete']:raise RuntimeError('Real UE render incomplete')
if not json.loads((O/'Reports/visual-review.json').read_text())['ready_to_apply']:raise RuntimeError('Visual review incomplete')
if not json.loads((O/'Reports/saved-assets-check.json').read_text())['passed']:raise RuntimeError('Candidate asset readback incomplete')
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;LS=u.GeometryScript_List;ED=u.GeometryScript_MeshEdits;SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);SK=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
sys.path.insert(0,str(P/'Tools/Saiga12KClosure'));from mesh_contract import arm_contract
receipt=json.loads((O/'Receipts/assets.json').read_text());result=json.loads((O/'Receipts/activation.json').read_text()) if (O/'Receipts/activation.json').exists() else {'complete':False,'updated':{},'runtime_paths_unchanged':True,'gameplay_unchanged':True}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(ACTIVE) for p in dirty):raise RuntimeError('Unsaved active Saiga asset; preserve edits')
def read_skeletal(mesh):return G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())[0]
for key in receipt['bindings']:
 if key in result['updated']:continue
 relative='/SK_Saiga12K_Manny' if key=='native' else '/SM_Saiga12K_Ext12' if key=='ext12' else '/Attachments/SM_Saiga12K_'+key
 source=u.load_asset(D+relative);target=u.load_asset(ACTIVE+relative)
 file=P/('Content'+ACTIVE.removeprefix('/Game')+relative+'.uasset');backup=O/'SourceBefore'/file.relative_to(P);backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(file,backup)
 if key=='native':
  before=arm_contract(target);dm=read_skeletal(source);slots=list(source.materials);opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
  _,status=G.copy_mesh_to_skeletal_mesh(dm,target,opts,u.GeometryScriptMeshWriteLOD())
  if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Active native copy failed')
  donor='/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative';payload=json.loads((P/'SourceAssets/BareSkinV9Rollout_20261017/Work/batch1'/(hashlib.sha256(donor.encode()).hexdigest()[:12]+'.json')).read_text());_,ps,_=Q.get_all_vertex_positions(read_skeletal(target),False);mapping={}
  for i,p in enumerate(LS.convert_vector_list_to_array(ps)):mapping.setdefault(tuple(round(v,4) for v in (p.x,p.y,p.z)),[]).append(i)
  oldmap={vi:mapping.get(tuple(round(x,4) for x in p),[]) for vi,p in zip(payload['vertex_ids'],payload['positions'])}
  for name,rows in payload['morphs'].items():
   md=read_skeletal(target)
   for old,x,y,z,nx,ny,nz in rows:
    for vi in oldmap.get(old,[]):ED.set_vertex_position(md,vi,u.Vector(x,y,z),True)
   _,status=G.copy_morph_target_to_skeletal_mesh(md,target,name,u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True,emit_transaction=False,defer_mesh_post_edit_change=False,copy_normals=False),u.GeometryScriptMeshWriteLOD())
   if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Active morph restore failed '+name)
  SK.set_lod_build_settings(target,0,SK.get_lod_build_settings(source,0))
  if arm_contract(target)!=before:raise RuntimeError('Active native arm contract changed')
 else:
  dm,status=G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());slots=list(source.static_materials)
  _,status=G.copy_mesh_to_static_mesh(dm,target,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots]),u.GeometryScriptMeshWriteLOD())
  if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Active static copy failed '+key)
  target.set_editor_property('static_materials',slots)
  for li in range(SM.get_lod_count(source)):SM.set_lod_build_settings(target,li,SM.get_lod_build_settings(source,li))
 E.set_metadata_tag(target,'SaigaSurfaceRevision','Closure20261018; corrected UE clockwise winding, authored normals, repaired shells')
 E.set_metadata_tag(target,'SaigaAuthoringEntry','Tools/Saiga12KClosure/author_repair.py')
 if not E.save_loaded_asset(target,False):raise RuntimeError('Active save failed '+key)
 result['updated'][key]={'path':target.get_path_name(),'staged_source':source.get_path_name(),'backup':str(backup)};(O/'Receipts/activation.json').write_text(json.dumps(result,indent=2));print('ACTIVE_SAIGA_UPDATED',key,flush=True)
result['complete']=True;(O/'Receipts/activation.json').write_text(json.dumps(result,indent=2));print('SAIGA_ACTIVE_REPAIR_COMPLETE',len(result['updated']))
