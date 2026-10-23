"""Sample authored torso animation inputs only; no world, player or save slots."""
import json,math
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'Saved/SlingMotionDiagnosis20261022';R.mkdir(exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
samples={}
for key in ['Unarmed.Walk.Fwd','Unarmed.Jog.Fwd','Rifle.Walk.Fwd','Rifle.Jog.Fwd']:
    clip=u.load_asset(cfg['clips'][key])
    if not clip:raise RuntimeError('Missing animation '+key)
    length=clip.get_play_length();rows=[]
    for n in range(int(math.ceil(length*60))+1):
        t=min(n/60.,length);pose=u.Transform()
        for bone in ['pelvis','spine_01','spine_02','spine_03']:
            local=u.AnimationLibrary.get_bone_pose_for_time(clip,bone,t,False)
            pose=u.MathLibrary.compose_transforms(local,pose)
        v=pose.translation;q=pose.rotation
        rows.append({'time':t,'position':[v.x,v.y,v.z],'rotation':[q.x,q.y,q.z,q.w]})
    samples[key]={'source':clip.get_path_name(),'length':length,'root_translation_excluded':True,'samples':rows}
    print('BACKPACK_INPUT_SAMPLED',key,len(rows),flush=True)
(R/'animation_inputs.json').write_text(json.dumps(samples,separators=(',',':')))
print('BACKPACK_INPUT_SAMPLES_SAVED; no player or world created',flush=True)
