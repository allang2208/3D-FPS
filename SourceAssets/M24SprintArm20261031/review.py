from pathlib import Path
exec(compile((Path(__file__).parent/'solve.py').read_text().split("\nif __name__=='__main__':")[0],'solver','exec'))
patch=json.loads((O/'profile_patch.json').read_text());report={};folder=O/'AfterViews';folder.mkdir(exist_ok=True)
def delta(a,b):return (a.translation-b.translation).length*1000
for family in ('base','mag10'):
    metrics={'hand_contact_delta_mm':0.,'right_chain_delta_mm':0.,'gun_delta_mm':0.,'bone_length_delta_mm':0.,'max_frame_elbow_step_mm_240hz':0.,'loop_seam_mm':0.,'idle_endpoint_delta_mm':0.,'other_entries_unchanged':True}
    for role in ('sprint_enter','sprint_loop','sprint_exit'):
        clip,old=entry_for(family,role);new=next(c for c in patch['profiles'][family] if c['base']==old['base']);duration=(clip['keys']-1)/30;prev=None
        for i in range(round(duration*480)+1):
            t=i/480;before,bl=local_pose(clip,old,t);after,al=local_pose(clip,new,t)
            for n in names:
                if under(n,'hand_l'):metrics['hand_contact_delta_mm']=max(metrics['hand_contact_delta_mm'],delta(before[n],after[n]))
                if under(n,'clavicle_r'):metrics['right_chain_delta_mm']=max(metrics['right_chain_delta_mm'],delta(before[n],after[n]))
                if n.startswith('WPN_'):metrics['gun_delta_mm']=max(metrics['gun_delta_mm'],delta(before[n],after[n]))
            for n,p in (('lowerarm_l','upperarm_l'),('hand_l','lowerarm_l')):
                metrics['bone_length_delta_mm']=max(metrics['bone_length_delta_mm'],abs((before[n].translation-before[p].translation).length-(after[n].translation-after[p].translation).length)*1000)
            if i%2==0:
                if prev is not None:metrics['max_frame_elbow_step_mm_240hz']=max(metrics['max_frame_elbow_step_mm_240hz'],delta(after['lowerarm_l'],prev))
                prev=after['lowerarm_l'].copy()
            if role=='sprint_enter' and i==0 or role=='sprint_exit' and i==round(duration*480):metrics['idle_endpoint_delta_mm']=max(delta(before[n],after[n]) for n in names)
        if role=='sprint_loop':
            start=local_pose(clip,new,0)[0];end=local_pose(clip,new,duration)[0];metrics['loop_seam_mm']=max(delta(start[n],end[n]) for n in names)
    for old in ue['profiles'][family]:
        if old['base'] not in patch['modified'][family]:assert old==next(c for c in patch['profiles'][family] if c['base']==old['base'])
    assert metrics['hand_contact_delta_mm']<.25 and metrics['bone_length_delta_mm']<.01,metrics
    assert metrics['right_chain_delta_mm']<.001 and metrics['gun_delta_mm']<.001 and metrics['idle_endpoint_delta_mm']<.01,metrics
    assert metrics['loop_seam_mm']<.05,metrics
    metrics['runtime_mixed_contact_delta_mm']=0.;metrics['samples']={}
    for p in [i/60 for i in range(61)]:
        for phase in (0,.25,.5,.75):
            before=runtime(p,phase,family);after=runtime(p,phase,family,patch['profiles'])
            metrics['runtime_mixed_contact_delta_mm']=max(metrics['runtime_mixed_contact_delta_mm'],delta(before['hand_l'],after['hand_l']))
    assert metrics['runtime_mixed_contact_delta_mm']<1.,metrics
    for p,phase in ((0,0),(.3,0),(.65,0),(1,0),(1,.25),(1,.5),(1,.75),(1,1)):
        after=runtime(p,phase,family,patch['profiles']);metrics['samples'][f'{p}_{phase}']=detailed(after)
        if family=='base':view(after,folder/f'{p}_{phase}.png')
    report[family]=metrics
(O/'review.json').write_text(json.dumps(report,indent=2));print('SPRINT_ARM_REVIEW',json.dumps({f:{k:v for k,v in m.items() if k!='samples'} for f,m in report.items()}),flush=True)
