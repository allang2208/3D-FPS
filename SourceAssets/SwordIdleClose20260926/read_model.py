import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
result=[]
for c in ['Idle','Inspect','TacticalSprint20260921/SprintEnter','TacticalSprint20260921/SprintExit']:
    folder,clip=c.rsplit('/',1) if '/' in c else ('',c)
    a=u.load_asset('/Game/Weapons/AzureRunesword20260913/'+(folder+'/' if folder else '')+'A_RuneSword_'+clip)
    m=a.get_editor_property('data_model_interface')
    r={'clip':c,'duration':a.get_play_length(),'model_class':str(type(m))}
    for name in ['get_number_of_frames','get_number_of_keys','get_frame_rate','get_play_length']:
        try:r[name]=str(getattr(m,name)())
        except Exception as e:r[name]=str(e)
    r['model_functions']=[n for n in dir(m) if any(s in n for s in ['frame','key','bone','rate','length'])]
    o=u.AnimPoseEvaluationOptions();o.evaluation_type=u.AnimDataEvalType.SOURCE
    r['evaluated']=[]
    for t in [0,a.get_play_length()*.5,a.get_play_length()]:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,o)
        x=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.LOCAL)
        r['evaluated'].append({'t':t,'p':[x.translation.x,x.translation.y,x.translation.z], 'q':[x.rotation.x,x.rotation.y,x.rotation.z,x.rotation.w]})
    result.append(r)
(P/'model_read.json').write_text(json.dumps(result,indent=2))
