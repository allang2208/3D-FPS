"""Build and save Jason-native skeletal clothing from fitted authoring inputs."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonPlayer20261003')
manifest=json.loads((ROOT/'fitted_assets.json').read_text())
target=u.load_asset('/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body')
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
def copy(asset):
    dm,out=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if out!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy '+asset.get_path_name())
    return dm
target_dm=copy(target)
head=u.load_asset('/Game/AsianMale_Jason/Mesh/Head/SKM_Jason_head')
head_dm=copy(head)
_,hp,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(head_dm,False)
_,ht,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(head_dm,False)
hp=u.GeometryScript_List.convert_vector_list_to_array(hp);ht=u.GeometryScript_List.convert_triangle_list_to_array(ht)
(ROOT/'head_geometry.json').write_text(json.dumps({'positions':[[p.x,p.y,p.z] for p in hp],
    'triangles':[[p.x,p.y,p.z] for p in ht], 'materials':[{'slot':str(m.material_slot_name),'asset':m.material_interface.get_path_name()} for m in head.materials],
    'body_lods':u.SkeletalMeshEditorSubsystem.get_lod_count(target),'head_lods':u.SkeletalMeshEditorSubsystem.get_lod_count(head)},separators=(',',':')))
receipt=ROOT/'outfit_assets_saved.json'
saved=json.loads(receipt.read_text()) if receipt.exists() else {}
for key,path in manifest.items():
    data=json.loads((ROOT/('base_fitted.json' if key=='base' else key+'_fitted.json')).read_text())
    dm=copy(u.load_asset(data['source']))
    if key!='base':
        B.copy_bones_from_mesh(target_dm,dm,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=False))
        positions=u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*v) for v in data['positions']])
        u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,positions)
        for vi,weights in enumerate(data['weights']):
            B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=bone,weight=weight) for bone,weight in weights])
    else:
        for ti,mi in enumerate(data['triangle_materials']):
            u.GeometryScript_Materials.set_triangle_material_id(dm,ti,mi,True)
    # The old world sweaters bundle Manny's exposed skin/head into the garment.
    # Jason's separate native base owns those surfaces now.
    skin_slots=[i for i,m in enumerate(data['materials']) if m['slot'].startswith('Exposed')]
    if skin_slots:
        remove=[]
        for ti in range(dm.get_triangle_count()):
            material,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
            if valid and material in skin_slots:remove.append(ti)
        u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,u.GeometryScript_List.convert_array_to_index_list(remove),True)
    options=u.GeometryScriptCreateNewSkeletalMeshAssetOptions()
    options.use_mesh_bone_proportions=True
    options.enable_recompute_normals=key!='base';options.enable_recompute_tangents=True
    options.materials={m['slot']:u.load_asset(m['asset']) for m in data['materials']}
    existing=u.load_asset(path)
    if existing:
        receipt=ROOT/'outfit_assets_saved.json'
        if not receipt.exists() or key not in json.loads(receipt.read_text()):raise RuntimeError('Unowned existing output: '+path)
        write=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
            new_materials=[u.load_asset(m['asset']) for m in data['materials']],new_material_slot_names=[m['slot'] for m in data['materials']],
            enable_recompute_normals=key!='base',enable_recompute_tangents=True,
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,result=G.copy_mesh_to_skeletal_mesh(dm,existing,write,u.GeometryScriptMeshWriteLOD());asset=existing
    else:asset,result=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,target.skeleton,path,options)
    if result!=u.GeometryScriptOutcomePins.SUCCESS or not asset:raise RuntimeError('Create failed '+path)
    # Same distance-LOD authoring policy already used by the project's outfits.
    u.FPSModularOutfitComponent.configure_outfit_lods(asset)
    if not u.SkeletalMeshEditorSubsystem.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD build failed '+path)
    asset.set_editor_property('physics_asset',target.physics_asset)
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+path)
    saved[key]=asset.get_path_name()
    (ROOT/'outfit_assets_saved.json').write_text(json.dumps(saved,indent=2))
    print('JASON_OUTFIT_SAVED '+key+' '+asset.get_path_name(),flush=True)
print('JASON_OUTFITS_COMPLETE '+str(len(saved)),flush=True)
