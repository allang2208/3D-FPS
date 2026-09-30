"""Explicit rollback entry. Do not run during installation.

Uses the independently saved pre-R30 UE assets and preserves both generations.
Run through the project's existing serialized editor bridge when requested.
"""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;r=json.loads((O/'delivery.json').read_text())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Stop PIE before restoring model assets')
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils
dirty={x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in r['backups']):raise RuntimeError('A target 201 package has unsaved changes; preserve it')
restored=[]
for path,info in r['backups'].items():
 old=u.load_asset(info['asset']);target=u.load_asset(path)
 if isinstance(old,(u.SkeletalMesh,u.StaticMesh)):
  skeletal=isinstance(old,u.SkeletalMesh)
  read=G.copy_mesh_from_skeletal_mesh if skeletal else G.copy_mesh_from_static_mesh
  write=G.copy_mesh_to_skeletal_mesh if skeletal else G.copy_mesh_to_static_mesh
  dm,outcome=read(old,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
  if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot load previous surface '+path)
  prop='materials' if skeletal else 'static_materials';slots=[s.copy() for s in old.get_editor_property(prop)]
  opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],
   new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,
   bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
  _,outcome=write(dm,target,opt,u.GeometryScriptMeshWriteLOD())
  if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot restore surface '+path)
  target.set_editor_property(prop,slots)
  filenames=old.get_editor_property('asset_import_data').extract_filenames()
  if filenames:target.get_editor_property('asset_import_data').scripted_add_filename(filenames[0],0,'Restored pre-R30')
  E.set_metadata_tag(target,'201Revision','Restored pre-R30 model; R30 assets retained')
 else:
  # Only remove this revision's wet mappings. Keep later unrelated additions.
  previous=dict(old.get_editor_property('wet_materials'));current=dict(target.get_editor_property('wet_materials'))
  for mat in r.get('materials',{}).values():
   if mat not in previous:current.pop(mat,None)
  target.set_editor_property('wet_materials',current)
 if not E.save_loaded_asset(target,False):raise RuntimeError('Restore save failed '+path)
 restored.append(path)
manifest=O.parent/'Material21/bindings.json';live=json.loads(manifest.read_text());prior=json.loads((O/'Before/Material21_bindings.json').read_text())
for path in restored:
 key=path+'.'+path.rsplit('/',1)[1]
 if key in prior['meshes']:live['meshes'][key]=prior['meshes'][key]
manifest.write_text(json.dumps(live,indent=2),encoding='utf8')
(O/'restore_receipt.json').write_text(json.dumps({'restored':restored,'old_or_new_assets_deleted':False,'tested':False},indent=2))
print('PRE_R30_RESTORED',restored,flush=True)
