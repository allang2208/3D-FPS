"""Read donor timing/leg tracks to author slide cuts; no gameplay or rendering."""
import json
from pathlib import Path
import unreal as u
ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonSlide20261005'
receipt = json.loads((OUT/'assets-saved.json').read_text(encoding='utf-8'))
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = u.load_asset(cfg['body_mesh'])
bones = ['root','pelvis','thigh_l','calf_l','foot_l','ball_l','thigh_r','calf_r','foot_r','ball_r']
result = {}
for role,path in receipt['runtime_clips'].items():
    clip = u.load_asset(path); length = clip.get_play_length()
    rows = []
    for i in range(round(length*30)+1):
        t = min(i/30,length)
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
        row = {'t':t,'bones':{}}
        for bone in bones:
            tf = u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.WORLD)
            v,q = tf.translation,tf.rotation
            row['bones'][bone] = {'p':[v.x,v.y,v.z],'q':[q.x,q.y,q.z,q.w]}
        rows.append(row)
    result[role] = {'length':length,'samples':rows}
(OUT/'source-poses.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print('SLIDE_TIMING_READ',len(result))
