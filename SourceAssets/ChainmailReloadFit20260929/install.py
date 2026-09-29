"""Save isolated fitted garment assets and their three LODs, no gameplay edits."""
import json,unreal as u
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ChainmailReloadFit20260929')
def read(p):return json.loads(p.read_text())
E=u.EditorAssetLibrary;B=u.GeometryScript_BoneWeights;G=u.GeometryScript_AssetUtils
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
saved={}
for rig,entry in read(R/'sources.json').items():
 source=entry['shirt'];dest='/Game/Characters/ModularOutfit20260924/ChainmailReloadFit20260929/'+rig+'/SK_'+rig+'_Chainmail_Fitted'
 mesh=u.load_asset(source);dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read '+source)
 _,bones=B.get_all_bones_info(dm);ids={str(b.name):b.index for b in bones}
 for row in read(R/(rig+'_edits.json')):
  if 'position' in row:u.GeometryScript_MeshEdits.set_vertex_position(dm,row['vertex_id'],u.Vector(*row['position']),True)
  _,valid=B.set_vertex_bone_weights(dm,row['vertex_id'],[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in row['weights'].items()])
  if not valid:raise RuntimeError('Vertex '+str(row['vertex_id']))
 asset=u.load_asset(dest) or E.duplicate_asset(source,dest);slots=list(mesh.get_editor_property('materials'))
 opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[m.material_interface for m in slots],new_material_slot_names=[m.material_slot_name for m in slots],enable_recompute_normals=rig in ['ASH12','M16'],enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write '+rig)
 if not u.FPSModularOutfitComponent.configure_outfit_lods(asset) or not S.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD '+rig)
 E.set_metadata_tag(asset,'SourceContract','Native arm barycentric sleeve weights; existing geometry, layered cuff, sway masks preserved; 201 ADS34 right shoulder retained')
 asset.modify()
 if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):raise RuntimeError('Save '+rig)
 # Recollect installed weights for the per-animation offline comparison.
 dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Readback '+rig)
 _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones};d=read(R/(rig+'_fitted.json'))
 for i in range(len(d['positions'])):
  _,ws,valid=B.get_vertex_bone_weights(dm,i)
  if not valid:raise RuntimeError('Readback vertex '+rig+str(i))
  d['weights'][i]={names[w.bone_index]:w.weight for w in ws if w.weight>0}
 d['source']=asset.get_path_name();(R/(rig+'_saved.json')).write_text(json.dumps(d,separators=(',',':')))
 saved[rig]=dict(asset=asset.get_path_name(),previous=source,lods=3)
 (R/'saved.json').write_text(json.dumps(saved,indent=2));print('CHAINMAIL_SAVED',rig,flush=True)
