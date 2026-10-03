"""Save the corrected Jason garments, covered hip section, and bound backpack.

Run in the existing editor with PIE stopped, or in a background commandlet
after the editor is closed. No scene changes or runtime tests.
"""
import json
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME')
INPUT=PROJECT/'SourceAssets/JasonPlayer20261003'
ROOT=PROJECT/'SourceAssets/JasonEquipmentRepair20261003'
DEST='/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003'
BACKPACK_ONLY=globals().get('BACKPACK_ONLY',False) or '-JasonBackpackOnly' in u.SystemLibrary.get_command_line()
STRAPS_ONLY=globals().get('STRAPS_ONLY',False)
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('Stop PIE before saving the fitted equipment assets.')
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
target=u.load_asset('/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body')
def read(p):return json.loads(p.read_text())
def skeletal_copy(asset):
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot extract '+asset.get_path_name())
    return dm
target_dm=skeletal_copy(target)
receipt=ROOT/'assets_saved.json'
saved=read(receipt) if receipt.exists() else {}

def save_skeletal(key,dm,materials,path,recompute=True,lods=True):
    options=u.GeometryScriptCreateNewSkeletalMeshAssetOptions()
    options.use_mesh_bone_proportions=True
    options.enable_recompute_normals=recompute;options.enable_recompute_tangents=True
    options.materials={m['slot']:u.load_asset(m['asset']) for m in materials}
    existing=u.load_asset(path)
    if existing:
        write=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
            new_materials=[u.load_asset(m['asset']) for m in materials],
            new_material_slot_names=[m['slot'] for m in materials],enable_recompute_normals=recompute,
            enable_recompute_tangents=True,
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,status=G.copy_mesh_to_skeletal_mesh(dm,existing,write,u.GeometryScriptMeshWriteLOD());asset=existing
    else:
        asset,status=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,target.skeleton,path,options)
    if status!=u.GeometryScriptOutcomePins.SUCCESS or not asset:raise RuntimeError('Skeletal authoring failed '+path)
    if lods:
        u.FPSModularOutfitComponent.configure_outfit_lods(asset)
        if not u.SkeletalMeshEditorSubsystem.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD authoring failed '+path)
    asset.set_editor_property('physics_asset',target.physics_asset)
    if key=='base':asset.set_editor_property('post_process_anim_blueprint',target.get_editor_property('post_process_anim_blueprint'))
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+path)
    saved[key]=asset.get_path_name();receipt.write_text(json.dumps(saved,indent=2))
    print('JASON_EQUIPMENT_ASSET_SAVED '+key,flush=True)
    return asset

for key in ([] if BACKPACK_ONLY else read(INPUT/'fitted_assets.json')):
    data=read(INPUT/('base_fitted.json' if key=='base' else key+'_fitted.json'))
    dm=skeletal_copy(u.load_asset(data['source']))
    if key=='base':
        remove=[]
        for ti,mi in enumerate(data['triangle_materials']):
            u.GeometryScript_Materials.set_triangle_material_id(dm,ti,mi,True)
            if mi in (5,6):remove.append(ti)
    else:
        B.copy_bones_from_mesh(target_dm,dm,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=False))
        u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*p) for p in data['positions']]))
        for vi,weights in enumerate(data['weights']):
            B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=b,weight=w) for b,w in weights])
        hidden=[i for i,m in enumerate(data['materials']) if m['slot'].startswith('Exposed')]
        remove=[ti for ti in range(dm.get_triangle_count()) if u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0] in hidden]
    if remove:u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,u.GeometryScript_List.convert_array_to_index_list(remove),True)
    save_skeletal(key,dm,data['materials'],DEST+'/SK_Jason_'+('Base' if key=='base' else key),recompute=key!='base')

data=read(ROOT/'backpack_fitted.json')
dm,status=G.copy_mesh_from_static_mesh(u.load_asset(data['source']),u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Backpack extraction failed')
if data['flip_winding']:u.GeometryScript_Normals.flip_normals(dm)
# An opaque native PBR copy serves both the corrected icon source and skeletal pack.
mat_path=DEST+'/M_SovietBackpack_Fitted'
mat=u.load_asset(mat_path) or u.EditorAssetLibrary.duplicate_asset(data['materials'][0]['asset'],mat_path)
if not mat:raise RuntimeError('Cannot author backpack material')
if not STRAPS_ONLY:
    u.MaterialEditingLibrary.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    u.MaterialEditingLibrary.recompile_material(mat)
    if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Backpack material save failed')
data['materials'][0]['asset']=mat.get_path_name()
if not STRAPS_ONLY:
    static_path=DEST+'/SM_SovietBackpack_Corrected'
    static=u.load_asset(static_path) or u.EditorAssetLibrary.duplicate_asset(data['source'],static_path)
    if not static:raise RuntimeError('Cannot create static icon source')
    write=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True)
    _,status=G.copy_mesh_to_static_mesh(dm,static,write,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Backpack winding save failed')
    static.set_material(0,mat)
    if not u.EditorAssetLibrary.save_loaded_asset(static,False):raise RuntimeError('Static backpack save failed')
    saved['backpack_static']=static.get_path_name()
B.copy_bones_from_mesh(target_dm,dm,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=False))
B.mesh_create_bone_weights(dm)
u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*p) for p in data['positions']]))
for vi,weights in enumerate(data['weights']):
    B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=b,weight=w) for b,w in weights])
save_skeletal('backpack',dm,data['materials'],DEST+'/SK_Jason_Backpack',lods=False)
bone=target.skeleton.get_reference_pose().get_bone_pose('spine_03',u.AnimPoseSpaces.WORLD)
desired=u.Transform();desired.translation=u.Vector(0,-10.5,120)
desired.rotation=u.Rotator(0,180,0).quaternion();desired.scale3d=u.Vector(.9,.9,.9)
rel=desired.make_relative(bone);r=rel.rotation.rotator();p=rel.translation;s=rel.scale3d
saved['static_fallback_transform']={'attach_bone':'spine_03','attach_location':[p.x,p.y,p.z],
    'attach_rotation':[r.pitch,r.yaw,r.roll],'attach_scale':[s.x,s.y,s.z]}
receipt.write_text(json.dumps(saved,indent=2))
if STRAPS_ONLY:
    (ROOT/'ShoulderStraps'/'saved.json').write_text(json.dumps({'asset':saved['backpack'],
        'fit':data.get('shoulder_fit'),'saved':True,'runtime_tested':False},indent=2))
print('JASON_EQUIPMENT_ASSETS_COMPLETE',flush=True)
