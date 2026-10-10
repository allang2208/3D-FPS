"""Read only the locomotion poses implicated in the reported prop clipping."""
import json
from pathlib import Path
import unreal as u
root=Path('D:/FPS3D/FPSGAME')
out=root/'SourceAssets/ThirdPersonStaffCarryClearance20261010'
cfg=json.loads((root/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
mesh=u.load_asset(cfg['body_mesh'])
names=json.loads((out/'authored.json').read_text())['names']
opt=u.AnimPoseEvaluationOptions()
opt.optional_skeletal_mesh=mesh
opt.evaluation_type=u.AnimDataEvalType.SOURCE
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
keys=['Unarmed.Idle']+[f'Unarmed.{pace}.{direction}' for pace in ['Walk','Jog'] for direction in ['Fwd','Bwd','Left','Right']]
result={}
for key in keys:
    clip=u.load_asset(cfg['clips'][key]);duration=clip.get_play_length()
    frames=[]
    for i in range(16):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*i/16,opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
    result[key]=dict(asset=clip.get_path_name(),duration=duration,frames=frames)
(out/'gaits.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print('STAFF_CARRY_GAITS_READ',list(result))
