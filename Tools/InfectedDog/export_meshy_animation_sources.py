"""Export existing, accepted canine motion as authoring input. No game run."""
import json, math
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/InfectedDogMeshy20260924/CompletionV2'
OUT.mkdir(parents=True,exist_ok=True)
source=json.loads((OUT/'source_action_bindings.json').read_text(encoding='utf-8'))
mesh=u.load_asset('/Game/AnimalVarietyPack/Wolf/Meshes/SK_Wolf')
comp=u.SkeletalMeshComponent(); comp.set_skeletal_mesh_asset(mesh)
names=[str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
parents={n:str(comp.get_parent_bone(n)) for n in names}
opts=u.AnimPoseEvaluationOptions()
opts.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
opts.set_editor_property('optional_skeletal_mesh',mesh)
def unpack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.x,q.y,q.z,q.w],'s':[s.x,s.y,s.z]}
data={'names':names,'parents':parents,'clips':{},'source_mesh':mesh.get_path_name()}
for role,path in source['clips'].items():
    clip=u.load_asset(path)
    if clip is None: raise RuntimeError('Required source clip missing: '+path)
    duration=clip.get_play_length(); count=round(duration*60)
    frames=[]
    for i in range(count+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*i/count,opts)
        if 'rest' not in data:
            data['rest']={n:unpack(u.AnimPoseExtensions.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
        frames.append({n:unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
    data['clips'][role]={'source':path,'seconds':duration,'intervals':count,'fps':count/duration,'world':frames}
    u.log('MESHY_SOURCE_EXPORTED '+role+' '+str(count+1))
(OUT/'wolf_motion_sources.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
u.log('MESHY_ANIMATION_SOURCES_SAVED '+str(OUT))
