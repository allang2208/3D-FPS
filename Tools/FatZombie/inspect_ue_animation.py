"""Read the imported runtime pose, including the mesh's retarget settings."""
import unreal as u
import json, os, math
from pathlib import Path

folder='/Game/Monsters/FatZombieMeshy'
output=Path('D:/FPS3D/FPSGAME/Saved/FatZombieContinuity')
output.mkdir(parents=True,exist_ok=True)
mesh=u.load_asset(folder+'/SK_FatZombie_Meshy')
options=u.AnimPoseEvaluationOptions()
options.set_editor_property('evaluation_type',u.AnimDataEvalType.COMPRESSED)
options.set_editor_property('optional_skeletal_mesh',mesh)
options.set_editor_property('incorporate_root_motion_into_pose',False)
names=['FatZombieRoot','Hips','Head','LeftFoot','RightFoot','LeftHand','RightHand']
report={}
for role in ['Idle','Walk','Attack','Death']:
    clip=u.load_asset(folder+'/Animations/A_FatZombie_'+role)
    length=clip.get_play_length()
    count=round(length*120)
    samples=[]
    for i in range(count+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,length*i/count,options)
        frame={}
        for n in names:
            p=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD).translation
            frame[n]=[p.x,p.y,p.z]
        samples.append(frame)
    stats={}
    for n in names:
        p=[s[n] for s in samples]
        stats[n]={'first_cm':p[0],'last_cm':p[-1],
                  'range_cm':[max(v[a] for v in p)-min(v[a] for v in p) for a in range(3)],
                  'max_step_cm':max(math.dist(p[i],p[i-1]) for i in range(1,len(p))),
                  'seam_cm':math.dist(p[0],p[-1])}
    report[role]={'seconds':length,'root_lock':clip.get_editor_property('force_root_lock'),
                  'bones':stats,'positions_cm':samples}
    u.log('FAT_UE_CONTINUITY '+json.dumps({'role':role,**stats['Hips']}))
label=os.environ.get('FAT_ZOMBIE_REPORT_LABEL','before')
(output/('ue_compressed_'+label+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
