"""Read source/retarget knee bending and available Jason walk references, without playing."""
import json
import math
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ThirdPersonKnees20261003'
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
original = json.loads((ROOT/'SourceAssets/JasonPlayer20261003/Before/Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
result = {}
for label, config in [('source', original), ('jason', cfg), ('native_demo', cfg)]:
    mesh = u.load_asset(config['body_mesh'])
    options = u.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh = mesh
    bones = ['root', 'pelvis']+[b+'_'+s for s in ('r','l') for b in ('thigh','calf','foot','ball')]
    clips = {k:v for k,v in config['clips'].items() if '.Walk.' in k or k.endswith('.Idle')}
    if label == 'native_demo':
        clips = {k:'/Game/AsianMale_Jason/Demo/Animation/'+k for k in ('AS_Jason_Idle','AS_Jason_Walk_Fwd','AS_Jason_Run_Fwd')}
    result[label] = {'mesh':mesh.get_path_name(),'clips':{}}
    for key, path in clips.items():
        clip = u.load_asset(path)
        if not isinstance(clip,u.AnimSequence):
            continue
        rows = []
        for i in range(65):
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/64,options)
            positions = {b:u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD).translation for b in bones}
            row = {'t':clip.get_play_length()*i/64,'bones':{b:[v.x,v.y,v.z] for b,v in positions.items()},'knees':{}}
            for s in ('r','l'):
                h,k,f = (positions[b+'_'+s] for b in ('thigh','calf','foot'))
                a,b = k-h,f-k
                dot = (a.x*b.x+a.y*b.y+a.z*b.z)/(a.length()*b.length())
                row['knees'][s] = {'flex':math.degrees(math.acos(max(-1,min(1,dot)))),
                    'upper':a.length(),'lower':b.length(),'reach':(f-h).length()/(a.length()+b.length())}
            rows.append(row)
        result[label]['clips'][key] = {'path':clip.get_path_name(),'seconds':clip.get_play_length(),
            'force_root_lock':clip.get_editor_property('force_root_lock'),
            'enable_root_motion':clip.get_editor_property('enable_root_motion'),'samples':rows}
(OUT/'knee-sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('KNEE_SOURCES_SAVED '+str(OUT/'knee-sources.json'))
