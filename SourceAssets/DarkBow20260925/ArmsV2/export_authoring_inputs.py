"""Read Sparrow's actual arm motion and the bow surface for authoring. No playback."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).parent
ROOT.mkdir(parents=True, exist_ok=True)
SP = '/Game/ParagonSparrow/Characters/Heroes/Sparrow'
mesh = u.load_asset(SP+'/Meshes/Sparrow')
dm, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
    mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if outcome != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot read Sparrow reference skeleton')
_, bones = u.GeometryScript_BoneWeights.get_all_bones_info(dm)
names = [str(b.name) for b in bones]
def transform(t):
    return {'p':[t.translation.x,t.translation.y,t.translation.z],
            'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],
            's':[t.scale3d.x,t.scale3d.y,t.scale3d.z]}
reference = {'bones': {str(b.name):dict(transform(b.world_transform), parent=b.parent_index, index=b.index) for b in bones}, 'clips':{}}
opt = u.AnimPoseEvaluationOptions()
opt.evaluation_type = u.AnimDataEvalType.SOURCE
opt.optional_skeletal_mesh = mesh
for clip in ('idle','RMB_Drawback','R_Ability_Fast_Fire'):
    asset = u.load_asset(SP+'/Animations/'+clip)
    length = asset.get_play_length()
    frames = []
    for frame in range(round(length*30)+1):
        t=min(frame/30,length)
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,opt)
        frames.append({n:transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
    reference['clips'][clip]={'source':asset.get_path_name(),'seconds':length,'fps':30,'frames':frames}
(ROOT/'sparrow_motion.json').write_text(json.dumps(reference,separators=(',',':')),encoding='utf-8')

bow = u.load_asset('/Game/Weapons/DarkBow20260925/SK_DarkBow')
dm,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(bow,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if outcome != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot read dark bow surface')
Q=u.GeometryScript_MeshQueries
_,v,_=Q.get_all_vertex_positions(dm,False)
_,t,_=Q.get_all_triangle_indices(dm,False)
vs=u.GeometryScript_List.convert_vector_list_to_array(v)
ts=u.GeometryScript_List.convert_triangle_list_to_array(t)
data={'positions':[[p.x,p.y,p.z] for p in vs],'triangles':[[p.x,p.y,p.z] for p in ts],
      'materials':[],'uv':[],'normals':[]}
for i in range(len(ts)):
    data['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
    a,b,c,valid=Q.get_triangle_u_vs(dm,0,i)
    data['uv'].append([[v.x,v.y] for v in (a,b,c)])
    _,a,b,c,valid=Q.get_triangle_normals(dm,i)
    data['normals'].append([[v.x,v.y,v.z] for v in (a,b,c)])
(ROOT/'bow_surface.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('BOW_AUTHORING_INPUTS_SAVED',len(names),list(reference['clips']),len(ts))
