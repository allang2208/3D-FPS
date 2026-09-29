"""Read the reported DW715 grip and saved steel mesh; no scene or asset writes."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1/GripFix'
R.mkdir(exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
def xyz(v):return [v.x,v.y,v.z]
def bone(t):return dict(position=xyz(t.translation),axes=[xyz(t.transform_location(v)-t.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))])
def write(name,d):(R/name).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')

path=cfg['items']['ue_steel_gauntlets']['rig_meshes']['DW715']
mesh=u.load_asset(path)
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
_,pos,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(pos)
_,tri,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(tri)
weights=[]
for i in range(len(ps)):
    _,ws,ok=B.get_vertex_bone_weights(dm,i)
    if not ok:raise RuntimeError('Cannot read bone weights')
    weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
d=dict(source=path,positions=[xyz(v) for v in ps],triangles=[xyz(t) for t in ts],weights=weights,
    triangle_materials=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(ts))],
    bones={str(b.name):dict(bone(b.world_transform),index=b.index,parent=b.parent_index) for b in bones})
write('DW715_saved_before.json',d)
native=u.load_asset('/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny')
opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED;opts.optional_skeletal_mesh=native
clips={}
for label in ('idle','aim'):
    path='/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_'+label
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing '+path)
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,0.,opts)
    clips[label]=dict(asset=path,time=0.,bones={n:bone(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in d['bones']})
write('DW715_poses.json',clips)
print('STEEL_GRIP_READ',len(ps),len(ts),list(clips),flush=True)
