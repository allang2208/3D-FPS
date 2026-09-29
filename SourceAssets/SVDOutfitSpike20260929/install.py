from pathlib import Path
import json,unreal as u
P=Path('D:/FPS3D/FPSGAME');exec((P/'SourceAssets/ChainmailReloadFit20260929/collect.py').read_text().split('manifest={}')[0]);R=P/'SourceAssets/SVDOutfitSpike20260929'
E=u.EditorAssetLibrary;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem);saved={}
for name,row in json.loads((R/'edits.json').read_text()).items():
 source=row['source'];mesh=u.load_asset(source);dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read '+name)
 _,bones=B.get_all_bones_info(dm);ids={str(b.name):b.index for b in bones}
 for edit in row['weights']:
  _,valid=B.set_vertex_bone_weights(dm,edit['vertex_id'],[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in edit['weights'].items()])
  if not valid:raise RuntimeError('Weight '+name)
 for ti in row['delete_triangles']:
  _,deleted=u.GeometryScript_MeshEdits.delete_triangle_from_mesh(dm,ti,True)
  if not deleted:raise RuntimeError('Delete closure '+name+str(ti))
 dest='/Game/Characters/ModularOutfit20260924/SVDShoulderOpening20260929/SK_SVD_'+name.removeprefix('ue_')
 asset=E.duplicate_asset(source,dest)
 if not asset:raise RuntimeError('Duplicate '+name)
 slots=list(mesh.get_editor_property('materials'));opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[m.material_interface for m in slots],new_material_slot_names=[m.material_slot_name for m in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write '+name)
 if not u.FPSModularOutfitComponent.configure_outfit_lods(asset) or not S.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD '+name)
 E.set_metadata_tag(asset,'SourceContract','Removed 240 erroneous shoulder hole-fill triangles; sleeves open towards torso; real arm surfaces and cuff retained');asset.modify()
 if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):raise RuntimeError('Save '+name)
 d=extract(asset.get_path_name());(R/(name+'_fixed.json')).write_text(json.dumps(d,separators=(',',':')))
 saved[name]=dict(source=source,asset=asset.get_path_name(),removed_triangles=240,lods=3)
 (R/'saved.json').write_text(json.dumps(saved,indent=2));print('SVD_SHOULDER_SAVED',name,flush=True)
