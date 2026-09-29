"""Save the scoped traversal short-sleeve skinning repair."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ShortSleeveTraversalFix20260929';DEST='/Game/Characters/ModularOutfit20260924/ShortSleeveTraversalFix20260929/SK_Traversal_Charcoal_Fitted'
def read(p):return json.loads(p.read_text())
source=read(R/'shirt.json')['source'];E=u.EditorAssetLibrary;B=u.GeometryScript_BoneWeights;G=u.GeometryScript_AssetUtils
mesh=u.load_asset(source);dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read source failed')
_,bones=B.get_all_bones_info(dm);ids={str(b.name):b.index for b in bones}
for row in read(R/'edits.json'):
 _,valid=B.set_vertex_bone_weights(dm,row['vertex_id'],[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in row['weights'].items()])
 if not valid:raise RuntimeError('Invalid vertex')
asset=u.load_asset(DEST) or E.duplicate_asset(source,DEST);slots=list(mesh.get_editor_property('materials'))
options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[m.material_interface for m in slots],new_material_slot_names=[m.material_slot_name for m in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write asset failed')
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
if not u.FPSModularOutfitComponent.configure_outfit_lods(asset) or not S.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD build failed')
E.set_metadata_tag(asset,'SourceContract','Traversal upper-arm barycentric skin weights; garment shape and rolled hem preserved');asset.modify()
if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):raise RuntimeError('Save failed')
# Read saved skin data for the same bounded offline comparison, not a game run.
dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Saved source unavailable')
Q=u.GeometryScript_MeshQueries;_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
_,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps);_,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
d=read(R/'shirt.json');d['source']=asset.get_path_name();d['positions']=[[v.x,v.y,v.z] for v in ps];d['triangles']=[[t.x,t.y,t.z] for t in ts];d['weights']=[];d['materials']=[]
for i in range(len(ps)):
 _,ws,valid=B.get_vertex_bone_weights(dm,i);d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
for i in range(len(ts)):d['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
(R/'shirt.json').write_text(json.dumps(d,separators=(',',':')))
export=u.AssetExportTask();export.object=asset;export.filename=str(R/'SK_Traversal_Charcoal_Fitted.fbx');export.automated=True;export.prompt=False;export.replace_identical=True;export.options=u.FbxExportOption();export.options.level_of_detail=False;export.options.export_morph_targets=False
if not u.Exporter.run_asset_export_task(export):raise RuntimeError('FBX export failed')
(R/'saved.json').write_text(json.dumps(dict(asset=asset.get_path_name(),previous=source,lods=3),indent=2));print('TRAVERSAL_SHIRT_SAVED',flush=True)
