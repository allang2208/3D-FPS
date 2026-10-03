"""Read authored mesh and clip transforms for the requested membrane diagnosis."""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/MembraneSkinV35')
OUT.mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07')
cdo=u.get_default_object(bp.generated_class())
props=('magic_attack','fireball_damage_multiplier','ice_column_damage_multiplier','lightning_damage_multiplier',
       'use_coherent_gill_motion','gill_clearance_angle_degrees','walk_speed','chase_speed')
report={'settings':{p:cdo.get_editor_property(p) for p in props},'clips':{},'runtime_tested':False}
def transform(t):
    q=t.rotation;p=t.translation;s=t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z],'s':[s.x,s.y,s.z]}
for prop in ('idle_clip','slow_walk_clip','chase_clip','melee_left_clip','melee_right_clip','magic_gather_clip','magic_release_clip'):
    clip=cdo.get_editor_property(prop)
    samples=[]
    for i in range(7):
        t=clip.get_play_length()*i/6
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,u.AnimPoseEvaluationOptions())
        names=u.AnimPoseExtensions.get_bone_names(pose)
        samples.append({'time':t,'bones':{str(n):transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}})
    report['clips'][prop]={'asset':clip.get_path_name(),'samples':samples}
ref=u.AnimPoseExtensions.get_reference_pose(cdo.get_editor_property('visual_mesh').get_editor_property('skeleton'))
report['reference']={str(n):transform(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in u.AnimPoseExtensions.get_bone_names(ref)}
(OUT/'current_ue_source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M07_V35_SOURCE_READ '+json.dumps(report['settings']))
