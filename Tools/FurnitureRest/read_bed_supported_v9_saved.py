"""Sample this revision's saved compressed clips for the requested offline review."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedSupportedV9'
source=json.loads((OUT/'authored.json').read_text())
body=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
receipt={role:body['clips'][role] for role in source['clips']}
mesh=u.load_asset(source['mesh'])
rig={k:source[k] for k in ('mesh','skeleton','names','parents','reference')};rig['clips']={}
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
source_opt=u.AnimPoseEvaluationOptions();source_opt.optional_skeletal_mesh=mesh;source_opt.evaluation_type=u.AnimDataEvalType.SOURCE
for role,path in receipt.items():
    clip=u.load_asset(path)
    if not clip or clip.get_editor_property('skeleton')!=mesh.skeleton:raise RuntimeError('Clip skeleton mismatch '+role)
    length=clip.get_play_length();frames=[];count=round(length*15)+1
    for i in range(count):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,length*i/(count-1),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in rig['names']])
    endpoints=[]
    for t in (0,length):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,source_opt)
        endpoints.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in rig['names']])
    rig['clips'][role]={'duration':length,'frames':frames,'asset':path,'source_endpoints':endpoints,'evaluation':'compressed'}
    print('BED_SUPPORTED_READBACK',role)
dest=OUT/'ReviewSaved';dest.mkdir(exist_ok=True)
(dest/'saved_poses.json').write_text(json.dumps(rig,separators=(',',':')))
print('BED_SUPPORTED_READBACK_COMPLETE',len(rig['clips']))
