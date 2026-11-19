import json, math
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME')
base=P/'SourceAssets/JasonStrong20261117'
out=base/'R4_PoseRefined/Review'
data=json.loads((base/'R3_ArmsRefined/variant_saved.json').read_text())
mesh=u.load_asset(data['asset'])
bones=json.loads((base/'R3_ArmsRefined/body_source.json').read_text())['bones']
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
opt=u.AnimPoseEvaluationOptions()
opt.optional_skeletal_mesh=mesh
opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
opt.incorporate_root_motion_into_pose=False
post=mesh.get_editor_property('post_process_anim_blueprint')
outdata={'post_process':post.get_path_name() if post else None,'poses':{}}
for key in ['Rifle.Idle','Rifle.Reload','Melee.FullBody.Slash1']:
    asset=cfg['clips'][key];clip=u.load_asset(asset)
    if not clip: raise ValueError(asset)
    for frac in [.15,.45,.7]:
        time=frac*clip.get_play_length()
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opt)
        mats=[]
        for b in bones:
            t=u.AnimPoseExtensions.get_bone_pose(pose,b['name'],u.AnimPoseSpaces.WORLD)
            mats.append([list(t.translation.to_tuple()),list(t.rotation.to_tuple()),list(t.scale3d.to_tuple())])
        outdata['poses'][f'{key}_{frac}']={'time':time,'asset':asset,'world':mats}
(out/'clips.json').write_text(json.dumps(outdata,separators=(',',':')))
print('R4_POSES_READY',list(outdata['poses']),outdata['post_process'])
