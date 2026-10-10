"""Save only the repaired Jason steel glove and merge its equipment reference."""
import json
from pathlib import Path
import unreal as u
root=Path('D:/FPS3D/FPSGAME');out=root/'SourceAssets/ThirdPersonStaffThumbSteel20261009'
data=json.loads((out/'steel-repaired.json').read_text())
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('Stop PIE before saving the repaired glove.')
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
source=u.load_asset(data['source'])
dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read the active Jason glove')
u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*p) for p in data['positions']]))
for vi,weights in enumerate(data['weights']):
    B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=b,weight=w) for b,w in weights])
path='/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/SteelRepair20261009/SK_Jason_SteelGauntlets'
asset=u.load_asset(path)
if asset:
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
else:
    options=u.GeometryScriptCreateNewSkeletalMeshAssetOptions(use_mesh_bone_proportions=True,
        enable_recompute_normals=True,enable_recompute_tangents=True)
    options.materials={m['slot']:u.load_asset(m['asset']) for m in data['materials']}
    asset,status=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,source.skeleton,path,options)
if status!=u.GeometryScriptOutcomePins.SUCCESS or not asset:raise RuntimeError('Glove authoring failed')
asset.set_editor_property('physics_asset',source.physics_asset)
u.FPSModularOutfitComponent.configure_outfit_lods(asset)
if not u.SkeletalMeshEditorSubsystem.regenerate_lod(asset,3,True,False):raise RuntimeError('Glove LOD generation failed')
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Glove save failed')
# Read the current file only after the asset has saved, then merge one field.
cfg_path=root/'Content/ColdSteelData/modular_outfits.json'
cfg=json.loads(cfg_path.read_text(encoding='utf-8-sig'))
current=cfg['items']['ue_steel_gauntlets']['rig_meshes']['Jason']
if current not in (data['source'],asset.get_path_name()):raise RuntimeError('Jason glove reference changed during authoring; saved asset retained without overriding it')
cfg['items']['ue_steel_gauntlets']['rig_meshes']['Jason']=asset.get_path_name()
cfg_path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt=dict(saved=True,asset=asset.get_path_name(),previous_asset=data['source'],vertices=len(data['positions']),
    triangles=len(data['triangles']),lods=3,materials=data['materials'],runtime_tested=False,
    config_change='items.ue_steel_gauntlets.rig_meshes.Jason')
(out/'asset-saved.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('JASON_STEEL_REPAIR_SAVED '+asset.get_path_name(),flush=True)
