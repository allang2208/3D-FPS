"""Read current melee configuration and authored contact poses; no runtime changes."""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/MeleeSpeed20261003')
OUT.mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07')
defaults=u.get_default_object(bp.generated_class())
properties=('walk_speed','chase_speed','source_walk_speed','source_chase_speed','attack_damage',
    'attack_range','sweep_hit_radius','left_contact_time','right_contact_time','contact_window_seconds','melee_playback_rate')
report={'settings':{p:defaults.get_editor_property(p) for p in properties},'clips':{}}
for prop,side in (('melee_left_clip','l'),('melee_right_clip','r')):
    clip=defaults.get_editor_property(prop)
    samples=[]
    for time in (.4,.5,.6,.7,.8):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,u.AnimPoseEvaluationOptions())
        positions={}
        for name in ('pelvis','foot_'+side,'ball_'+side,'lowerarm_'+side,'hand_'+side,'middle_03_'+side):
            p=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD).translation
            positions[name]=[p.x,p.y,p.z]
        samples.append({'time':time,'positions':positions})
    report['clips'][prop]={'asset':clip.get_path_name(),'samples':samples}
(OUT/'melee_source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
