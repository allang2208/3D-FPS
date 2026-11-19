"""Save a new body-only UE derivative; never change active player references."""
import json
import sys
from pathlib import Path
import unreal as u

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from muscle_shape import MuscleShape
from leg_proportions import LegProportions
PROJECT=Path('D:/FPS3D/FPSGAME')
OUT=Path(globals().get('variant_output',PROJECT/'SourceAssets/JasonStrong20261117/R2_LongLegs'))
MESH_NAME=globals().get('variant_mesh_name','SK_Jason_StrongTall_R2')
BLEND_NAME=globals().get('variant_blend_name','Jason_StrongTall_R2')
ShapeClass=globals().get('variant_shape_class',MuscleShape)
receipt=json.loads((OUT/'source_receipt.json').read_text())
source_path=receipt['assets']['body']['source']
dest='/Game/Characters/ModularOutfit20260924/JasonStrong20261117/'+OUT.name+'/'+MESH_NAME
source=u.load_asset(source_path)
seam=json.loads((OUT/'neck_seam.json').read_text())
if not source:raise RuntimeError('Missing source '+source_path)
if u.EditorAssetLibrary.does_asset_exist(dest):
    if not (OUT/'variant_owner.json').exists():
        raise RuntimeError('Destination already exists without this task ownership receipt')
    target=u.load_asset(dest)
    # Reset only this owned candidate's bind pose before rebuilding it from source.
    source_reader=u.SkeletonModifier();source_reader.set_skeletal_mesh(source)
    reset=u.SkeletonModifier();reset.set_skeletal_mesh(target)
    reset_names=source_reader.get_all_bone_names()
    reset.set_bones_transforms(reset_names,[source_reader.get_bone_transform(n,False) for n in reset_names],True)
    reset.commit_skeleton_to_skeletal_mesh()
else:
    target=u.EditorAssetLibrary.duplicate_asset(source_path,dest)
    if target:
        (OUT/'variant_owner.json').write_text(json.dumps({'asset':dest,'source':source_path}),encoding='utf-8')
if not target:raise RuntimeError('Could not duplicate Jason')
sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
lod_count=sub.get_lod_count(source)
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
lods=[]
source_bones=json.loads((OUT/'body_source.json').read_text())['bones']
proportions=LegProportions(source_bones)
source_bone_map={b['index']:b for b in source_bones}

def set_derived_bind_pose(mesh):
    modifier=u.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):raise RuntimeError('Cannot author derived bind pose')
    names,transforms=[],[]
    for bone in source_bones:
        parent=source_bone_map.get(bone['parent'])
        delta=proportions.offset(bone['position'][2])-(proportions.offset(parent['position'][2]) if parent else 0.)
        axes=parent['axes'] if parent else [[1,0,0],[0,1,0],[0,0,1]]
        local_delta=[delta*a[2]/sum(v*v for v in a) for a in axes]
        transform=modifier.get_bone_transform(bone['name'],False)
        transform.translation=transform.translation+u.Vector(*local_delta)
        names.append(bone['name']);transforms.append(transform)
    if not modifier.set_bones_transforms(names,transforms,True):raise RuntimeError('Cannot set longer-leg mesh bind pose')
    # Transform-only edits modify this mesh reference pose. The shared Skeleton is not merged or edited.
    if not modifier.commit_skeleton_to_skeletal_mesh():raise RuntimeError('Cannot commit derived mesh bind pose')

for lod in range(1):
    dm,result=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_index=lod))
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot extract source LOD '+str(lod))
    _,bones=B.get_all_bones_info(dm)
    shape=ShapeClass([{'name':str(b.name),'index':b.index,'parent':b.parent_index,
        'position':[b.world_transform.translation.x,b.world_transform.translation.y,b.world_transform.translation.z]} for b in bones],seam_segments=seam)
    _,plist,_=Q.get_all_vertex_positions(dm,False)
    positions=L.convert_vector_list_to_array(plist)
    revised=[]
    moved=[]
    for index,p in enumerate(positions):
        _,weights,valid=B.get_vertex_bone_weights(dm,index)
        original=[p.x,p.y,p.z]
        muscular=shape.deform(original,[(w.bone_index,w.weight) for w in weights])
        value=proportions.deform(original,muscular)
        revised.append(u.Vector(*value))
        if sum((a-b)**2 for a,b in zip(muscular,original))>1e-12 or proportions.foot_keep<p.z<proportions.hip:moved.append(index)
    u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,L.convert_array_to_vector_list(revised))
    _,selection=u.GeometryScript_MeshSelection.convert_index_list_to_mesh_selection(dm,
        L.convert_array_to_index_list(moved,u.GeometryScriptIndexType.VERTEX),u.GeometryScriptMeshSelectionType.VERTICES)
    u.GeometryScript_Normals.recompute_normals_for_mesh_selection(dm,selection,u.GeometryScriptCalculateNormalsOptions())
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
        replace_materials=True,new_materials=[s.material_interface for s in source.materials],
        new_material_slot_names=[s.material_slot_name for s in source.materials],
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,result=G.copy_mesh_to_skeletal_mesh(dm,target,options,u.GeometryScriptMeshWriteLOD(lod_index=lod))
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write variant LOD '+str(lod))
    if lod==0:
        set_derived_bind_pose(target)
    lods.append({'lod':lod,'vertices':len(positions)})
    print('JASON_STRONG_LOD_WRITTEN '+str(lod),flush=True)
if lod_count>1:
    if not sub.regenerate_lod(target,lod_count,True,False):raise RuntimeError('Cannot generate derived lower LODs')
    lods.extend({'lod':lod,'generated_from':0} for lod in range(1,lod_count))
target.set_editor_property('materials',source.materials)
if not u.EditorAssetLibrary.save_loaded_asset(target,False):raise RuntimeError('Variant asset save failed')
result={'asset':target.get_path_name(),'source':source_path,'skeleton':source.skeleton.get_path_name(),
    'authoring_project':u.Paths.get_project_file_path(),
    'saved_package_filename':u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir()+'Characters/ModularOutfit20260924/JasonStrong20261117/'+OUT.name+'/'+MESH_NAME+'.uasset'),
    'head':receipt['head_settings'],'materials':receipt['assets']['body']['materials'],'lods':lods,
    'lod0_topology_uv_weights_retained':True,'lower_lods_regenerated_from_derived_lod0':True,'shared_skeleton_asset_unchanged':True,
    'bone_names_and_hierarchy_retained':True,'derived_mesh_reference_pose_adjusted':True,
    'leg_height_increase_cm':proportions.total_gain,'calf_height_increase_cm':proportions.calf_gain,
    'thigh_height_increase_cm':proportions.thigh_gain,'head_preview_translation_z_cm':proportions.total_gain,
    'active_player_references_modified':False,'garment_fitting_performed':False,'gameplay_tested':False,
    'physics_asset':'Inherited original physics asset; no new body collision fitting performed.',
    'source_blend':str(OUT/(BLEND_NAME+'.blend'))}
(OUT/'variant_saved.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('JASON_STRONG_VARIANT_SAVED '+json.dumps(result),flush=True)
