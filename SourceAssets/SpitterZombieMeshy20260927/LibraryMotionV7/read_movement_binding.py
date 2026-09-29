"""Read only the Spitter movement defaults needed to diagnose the reported issue."""
import unreal as u
import json, math
from pathlib import Path
bp=u.load_asset('/Game/Monsters/SpitterZombie/BP_SpitterZombie')
cdo=u.get_default_object(bp.generated_class())
clips=cdo.get_editor_property('movement_clips')
report={'blueprint':bp.get_path_name(),'class':cdo.get_class().get_path_name(),
        'movement_clips':[a.get_path_name() if a else None for a in clips],
        'movement_reference_speeds':list(cdo.get_editor_property('movement_reference_speeds')),
        'fallback':cdo.get_editor_property('walk_clip').get_path_name(),
        'attack':cdo.get_editor_property('attack_clip').get_path_name(),
        'lengths':[a.get_play_length() if a else None for a in clips]}
mesh=cdo.get_editor_property('visual_mesh')
options=u.AnimPoseEvaluationOptions();options.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
options.set_editor_property('optional_skeletal_mesh',mesh)
names=['Hips','Spine02','Spine','LeftArm','RightArm','LeftUpLeg','RightUpLeg']
samples=[]
for clip in clips:
    frames=[]
    for phase in [0.,.25,.5,.75]:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*phase,options)
        row={}
        for bone in names:
            q=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.LOCAL).rotation
            row[bone]=[q.x,q.y,q.z,q.w]
        frames.append(row)
    samples.append(frames)
def angle(a,b):return math.degrees(2*math.acos(min(1,abs(sum(x*y for x,y in zip(a,b))))))
report['bone_rotation_differences_degrees']={}
for i in range(1,len(clips)):
    report['bone_rotation_differences_degrees'][clips[i].get_name()]={n:round(max(angle(a[n],b[n]) for a,b in zip(samples[0],samples[i])),2) for n in names}
report['temporal_pose_changes_degrees']={clips[i].get_name():round(max(angle(frames[0][n],f[n]) for f in frames[1:] for n in names),2) for i,frames in enumerate(samples)}
(Path(__file__).resolve().parent/'movement_binding_read.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('SPITTER_MOVEMENT_BINDING '+json.dumps(report))
