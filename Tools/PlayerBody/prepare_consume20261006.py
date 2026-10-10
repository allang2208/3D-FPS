"""Read saved food contact geometry and retarget the available CC0 Consume take."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/Consume20261006'
OUT.mkdir(parents=True,exist_ok=True)
DEST = '/Game/Characters/JasonPlayer20261003/Consume20261006'
lib = u.EditorAssetLibrary
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
source_info = json.loads((ROOT/'SourceAssets/ThirdPersonSwordDonorRepair20261006/imported-sources.json').read_text())
source = u.load_asset(source_info['mesh'])
target = u.load_asset(cfg['body_mesh'])
clip = u.load_asset(next(p for n,p in source_info['clips'].items() if n.endswith('_Consume')))
rtg = u.load_asset('/Game/Characters/JasonPlayer20261003/SwordDonorRepair20261006/Source/Rig/RTG_UAL2_Jason_Sword')
inputs = u.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget = [lib.find_asset_data(clip.get_path_name())]
inputs.source_mesh = source
inputs.target_mesh = target
inputs.ik_retarget_asset = rtg
inputs.prefix = 'J_'
inputs.target_path = DEST+'/Donor'
inputs.include_referenced_assets = False
inputs.overwrite_existing_files = False
retargeted = next(d.get_asset() for d in u.IKRetargetBatchOperation.run_batch_retarget(inputs) if isinstance(d.get_asset(),u.AnimSequence))
if not lib.save_loaded_asset(retargeted,False):
    raise RuntimeError('Failed saving consume donor')
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
def skeleton(mesh):
    ref = mesh.skeleton.get_reference_pose()
    names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
    comp = u.new_object(u.SkeletalMeshComponent)
    comp.set_skeletal_mesh_asset(mesh)
    parents = [names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names]
    return dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),names=names,parents=parents,
        reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names])
def read_clip(mesh,clip,names):
    options = u.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh = mesh
    options.evaluation_type = u.AnimDataEvalType.SOURCE
    length = clip.get_play_length()
    frames = []
    for i in range(round(length*30)+1):
        p = u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/30,length),options)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL)) for n in names])
    return dict(asset=clip.get_path_name(),duration=length,rate=30,frames=frames)
data = {}
for label,mesh,anim in [('source',source,clip),('target',target,retargeted)]:
    data[label] = skeleton(mesh)
    data[label]['clip'] = read_clip(mesh,anim,data[label]['names'])
data['target']['idle'] = read_clip(target,u.load_asset(cfg['clips']['Unarmed.Idle']),data['target']['names'])
(OUT/'donor.json').write_text(json.dumps(data,separators=(',',':')))

Q = u.GeometryScript_MeshQueries
L = u.GeometryScript_List
meshes = {}
paths = dict(baguette_bread='/Game/Items/Consumables/Baguette20261003/SM_Baguette',bread='/Game/Items/Consumables/Bread20261003/SM_Bread')
for name,path in paths.items():
    mesh = u.load_asset(path)
    lod = u.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type',u.GeometryScriptLODType.SOURCE_MODEL)
    dm,outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read saved food geometry '+path)
    _,vertices,_ = Q.get_all_vertex_positions(dm,False)
    _,triangles,_ = Q.get_all_triangle_indices(dm,False)
    bounds = mesh.get_bounds()
    meshes[name] = dict(asset=path,origin=list(bounds.origin.to_tuple()),extent=list(bounds.box_extent.to_tuple()),
        positions=[list(v.to_tuple()) for v in L.convert_vector_list_to_array(vertices)],
        triangles=[list(t.to_tuple()) for t in L.convert_triangle_list_to_array(triangles)])
(OUT/'food-geometry.json').write_text(json.dumps(meshes,separators=(',',':')))
print('CONSUME_INPUTS_SAVED '+str(OUT))
