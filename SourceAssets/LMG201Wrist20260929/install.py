"""Save a 201-only left wrist fix while preserving ADS34 right shoulder."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/LMG201Wrist20260929';DEST='/Game/Characters/ModularOutfit20260924/LMG201Wrist20260929/SK_LMG201_Chainmail_Wrist'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
source=read(R/'before.json');E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
mesh=u.load_asset(source['shirt']);dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read current 201 shirt')
_,bones=B.get_all_bones_info(dm);ids={str(b.name):b.index for b in bones}
for row in read(R/'edits.json'):
 _,valid=B.set_vertex_bone_weights(dm,row['vertex_id'],[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in row['weights'].items()])
 if not valid:raise RuntimeError('Missing native vertex')
 u.GeometryScript_MeshEdits.set_vertex_position(dm,row['vertex_id'],u.Vector(*row['position']),True)
asset=u.load_asset(DEST) or E.duplicate_asset(source['shirt'],DEST);slots=list(mesh.get_editor_property('materials'))
options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[m.material_interface for m in slots],new_material_slot_names=[m.material_slot_name for m in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write local wrist fix')
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
if not u.FPSModularOutfitComponent.configure_outfit_lods(asset) or not S.regenerate_lod(asset,3,True,False):raise RuntimeError('Wrist LOD build failed')
E.set_metadata_tag(asset,'WristFitSource',source['skin']);E.set_metadata_tag(asset,'PreservedRevision','ADS34 right shoulder and native 201 skeleton');asset.modify()
if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):raise RuntimeError('Wrist asset save failed')
export=u.AssetExportTask();export.object=asset;export.filename=str(R/'SK_LMG201_Chainmail_Wrist.fbx');export.automated=True;export.prompt=False;export.replace_identical=True;export.options=u.FbxExportOption();export.options.level_of_detail=False;export.options.export_morph_targets=False
if not u.Exporter.run_asset_export_task(export):raise RuntimeError('Editable FBX export failed')
path=P/'Content/ColdSteelData/modular_outfits.json';before=path.read_bytes();config=json.loads(before.decode('utf-8-sig'))
if config['items']['ue_chainmail_shirt']['rig_meshes']['LMG201']!=source['shirt'] or config['items']['ue_field_gloves']['skin_meshes']['LMG201']!=source['skin']:raise RuntimeError('201 equipment changed while authoring')
config['items']['ue_chainmail_shirt']['rig_meshes']['LMG201']=asset.get_path_name()
(R/'configuration-before.json').write_bytes(before);path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(R/'published.json').write_text(json.dumps(dict(asset=asset.get_path_name(),source=source,modified_profile='LMG201',left_vertices=len(read(R/'edits.json')),right_shoulder_preserved=True,lods=3,runtime_tested=False),indent=2))
print('201_WRIST_SAVED_AND_PUBLISHED',asset.get_path_name(),flush=True)
