"""Read existing accepted FPS contacts for authoring; no actors, saves or play."""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/SinglePistolHandContacts20261022')
models={
    'M1911':('/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny',
        '/Game/Weapons/M1911/Contact20260913/Animations/A_M1911_',
        '/Game/Weapons/M1911/ReloadReady20260913/Animations/A_M1911_'),
    'G18':('/Game/Weapons/G18/Integrated20260929/Single/SK_G18_Manny',
        '/Game/Weapons/G18/Integrated20260929/Single/Animations/A_G18_',
        '/Game/Weapons/G18/Integrated20260929/Single/Animations/A_G18_'),
    'PitViper2011':('/Game/Weapons/PitViper2011/Integrated20261002/Single/SK_PitViper2011_Manny',
        '/Game/Weapons/PitViper2011/Integrated20261002/Single/Animations/A_PitViper2011_',
        '/Game/Weapons/PitViper2011/Integrated20261002/Single/Animations/A_PitViper2011_')}
def load(path):
    obj=u.load_asset(path+'.'+path.rsplit('/',1)[-1])
    if obj is None: raise RuntimeError(path)
    return obj
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
rows={}
for model,(mp,idle,reload) in models.items():
    mesh=load(mp)
    options=u.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh=mesh;options.evaluation_type=u.AnimDataEvalType.SOURCE
    for side in ('r','l'):
        for role in ('idle','reload','reload_empty'):
            if side=='l':
                path=('/Game/Weapons/PitViper2011/LeftTwoHand20261020/A_PitViper_LeftTwoHand_' if model=='PitViper2011'
                    else f'/Game/Weapons/PistolLeftTwoHand20261020/{model}/A_LeftTwoHand_{model}_')+role
            else:path=(idle if role=='idle' else reload)+role
            clip=load(path);duration=clip.get_play_length()
            names=['hand_r','hand_l','WPN_root','WPN_SOCKET_Magazine']
            frames=[]
            for i in range(1 if role=='idle' else round(duration*30)+1):
                time=min(i/30,duration)
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,options)
                frames.append(dict(time=time,pose={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}))
            rows[model+'/'+side+'/'+role]=dict(asset=clip.get_path_name(),duration=duration,frames=frames)
(OUT/'fps-contact-inputs.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('SINGLE_PISTOL_CONTACT_INPUTS_SAVED')
