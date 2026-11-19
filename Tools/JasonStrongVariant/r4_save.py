"""Author mesh, morphs and a mesh-specific graph using only native runtime nodes."""
import json
from pathlib import Path
import unreal as u
base=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117')
out=base/'R4_PoseRefined'
review=out/'Review'
previous=json.loads((base/'R3_ArmsRefined/variant_saved.json').read_text())
r3=u.load_asset(previous['asset'])
asset_folder='/Game/Characters/ModularOutfit20260924/JasonStrong20261117/R4_PoseRefined'
dest=asset_folder+'/SK_Jason_StrongTall_R4'
graph_path=asset_folder+'/ABP_Jason_R4_Correctives'
lib=u.EditorAssetLibrary
sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
api=u.GeometryScript_AssetUtils
list_api=u.GeometryScript_List
read_lod=u.GeometryScriptMeshReadLOD(lod_index=0)
write_lod=u.GeometryScriptMeshWriteLOD(lod_index=0)
owner=out/'asset_owner.json'
if not owner.exists():
    if any(lib.does_asset_exist(path) for path in [dest,graph_path]):raise RuntimeError('Occupied R4 destination')
    owner.write_text(json.dumps([dest,graph_path]))
if json.loads(owner.read_text())!=[dest,graph_path]:raise RuntimeError('R4 owner mismatch')
mesh=u.load_asset(dest) if lib.does_asset_exist(dest) else lib.duplicate_asset(r3.get_path_name(),dest)
def extract(asset):
    dm,status=api.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),read_lod)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise ValueError('Could not read geometry')
    return dm
def set_points(dm,pts):
    u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,list_api.convert_array_to_vector_list([u.Vector(*p) for p in pts]))
def normals(dm,ids):
    _,selection=u.GeometryScript_MeshSelection.convert_index_list_to_mesh_selection(dm,list_api.convert_array_to_index_list(ids,u.GeometryScriptIndexType.VERTEX),u.GeometryScriptMeshSelectionType.VERTICES)
    u.GeometryScript_Normals.recompute_normals_for_mesh_selection(dm,selection,u.GeometryScriptCalculateNormalsOptions())
forms=json.loads((review/'forms.json').read_text());points=forms['base']
dm=extract(r3)
_,coords,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
coords=list_api.convert_vector_list_to_array(coords)
if len(coords)!=len(points):raise ValueError('Topology mismatch')
changed=[i for i,p in enumerate(coords) if abs(p.y-points[i][1])>1e-5]
set_points(dm,points);normals(dm,changed)
opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,new_materials=[s.material_interface for s in r3.materials],new_material_slot_names=[s.material_slot_name for s in r3.materials],bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,status=api.copy_mesh_to_skeletal_mesh(dm,mesh,opts,write_lod)
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise ValueError('Could not save chest shape')
morph_opts=u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True,emit_transaction=False,copy_normals=True)
for name,rows in forms['targets'].items():
    morph=extract(mesh);positions=points.copy()
    for i,x,y,z in rows:positions[i]=[points[i][0]+x,points[i][1]+y,points[i][2]+z]
    set_points(morph,positions);normals(morph,[r[0] for r in rows])
    _,status=api.copy_morph_target_to_skeletal_mesh(morph,mesh,name,morph_opts,write_lod)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise ValueError('Could not save '+name)
names=[f'R4_{part}_{side}' for side in 'lr' for part in ['Shoulder','Biceps']]
u.JasonReviewGraph.set_mesh_morph_flags(mesh,names)
lods=sub.get_lod_count(mesh)
if not sub.regenerate_lod(mesh,lods,True,False):raise ValueError('Could not map lower LODs')
post=r3.get_editor_property('post_process_anim_blueprint')
if post:raise ValueError('The R3 donor now has a post-process graph; chain this instead of replacing it')
if not lib.does_asset_exist(graph_path):
    factory=u.AnimBlueprintFactory()
    factory.set_editor_property('target_skeleton',mesh.skeleton)
    graph=u.AssetToolsHelpers.get_asset_tools().create_asset(graph_path.split('/')[-1],asset_folder,u.AnimBlueprint,factory)
    if not graph:raise ValueError('Cannot create graph')
    ok=u.JasonReviewGraph.add_drivers(graph,['upperarm_l','lowerarm_l','upperarm_r','lowerarm_r'],names,[1,2,1,2],[28.,11.,28.,11.],[64.,73.,64.,73.])
    if not ok:raise ValueError('Could not wire native pose graph')
    if not lib.save_loaded_asset(graph,False):raise ValueError('Graph save failed')
mesh.set_editor_property('post_process_anim_blueprint',lib.load_blueprint_class(graph_path))
if not lib.save_loaded_asset(mesh,False):raise ValueError('Mesh save failed')
result={'asset':mesh.get_path_name(),'post_process':mesh.get_editor_property('post_process_anim_blueprint').get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'morphs':names,'lods':lods,'source':previous['asset']}
(out/'variant_saved.json').write_text(json.dumps(result,indent=2))
print('R4_MESH_AND_GRAPH_SAVED',result)
