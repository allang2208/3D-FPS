"""Targeted checks requested for reload placement, hand-mag coupling and pacing."""
from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
tree=ast.parse((O/'author.py').read_text())
for name in ('source_frame',):exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
START=18.;END=25.25;KNOTS=[(18.,18.),(19.75,19.),(21.,21.),(22.,22.6),(24.,24.3),(25.25,25.25)]
patch=json.loads((O/'profile_patch.json').read_text());report={};folder=O/'Review';folder.mkdir(exist_ok=True)
def rotation_degrees(a,b):return math.degrees(a.to_quaternion().normalized().rotation_difference(b.to_quaternion().normalized()).angle)
def matrix_error(a,b):return max(abs(x-y) for va,vb in zip(a,b) for x,y in zip(va,vb))
for family in ('base','mag10'):
    report[family]={};normal,nentry=entry_for(family,'reload')
    for role in ('reload','reload_empty'):
        clip,old=entry_for(family,role);new=next(c for c in patch['profiles'][family] if c['base']==old['base'])
        metrics={k:0. for k in ('gun_position_cm','gun_rotation_deg','bolt_hand_position_cm','bolt_hand_rotation_deg','extraction_contact_cm','extraction_contact_deg','bone_length_delta_cm','extraction_start_end_error','outside_window_left_local_error','empty_support_position_cm')}
        frames=sorted({i/8 for i in range((clip['keys']-1)*8+1)}|{i/32 for i in range(568,817)})
        for f in frames:
            t=f/30;before,bl=local_pose(clip,old,t);after,al=local_pose(clip,new,t)
            normal_ref=local_pose(normal,nentry,min(f,normal['keys']-1)/30)[0] if role=='reload_empty' else before
            target=normal_ref['WPN_root']
            metrics['gun_position_cm']=max(metrics['gun_position_cm'],(after['WPN_root'].translation-target.translation).length*100)
            metrics['gun_rotation_deg']=max(metrics['gun_rotation_deg'],rotation_degrees(after['WPN_root'],target))
            for n in names:
                if under(n,'clavicle_r'):
                    a=before['WPN_root'].inverted()@before[n];b=after['WPN_root'].inverted()@after[n]
                    metrics['bolt_hand_position_cm']=max(metrics['bolt_hand_position_cm'],(a.translation-b.translation).length*100)
                    metrics['bolt_hand_rotation_deg']=max(metrics['bolt_hand_rotation_deg'],rotation_degrees(a,b))
                if under(n,'clavicle_l') and n!='clavicle_l':
                    metrics['bone_length_delta_cm']=max(metrics['bone_length_delta_cm'],abs(al[n].translation.length-bl[n].translation.length)*100)
                    if not START<f<END and not (role=='reload_empty' and f>=54):metrics['outside_window_left_local_error']=max(metrics['outside_window_left_local_error'],matrix_error(al[n],bl[n]))
                    if role=='reload_empty' and f>=54:
                        support_ref=normal_ref[n]
                        metrics['empty_support_position_cm']=max(metrics['empty_support_position_cm'],(after[n].translation-support_ref.translation).length*100)
            if START<=f<=END:
                donor=local_pose(clip,old,source_frame(f)/30)[0]
                for n in [n for n in names if under(n,'hand_l')]:
                    a=donor['WPN_Magazine'].inverted()@donor[n];b=after['WPN_Magazine'].inverted()@after[n]
                    metrics['extraction_contact_cm']=max(metrics['extraction_contact_cm'],(a.translation-b.translation).length*100)
                    metrics['extraction_contact_deg']=max(metrics['extraction_contact_deg'],rotation_degrees(a,b))
            if f in (START,END):metrics['extraction_start_end_error']=max(metrics['extraction_start_end_error'],max(matrix_error(al[n],bl[n]) for n in names if n!='VM_Root'))
        report[family][role]=metrics
        assert metrics['gun_position_cm']<.01 and metrics['gun_rotation_deg']<.1,metrics
        assert metrics['bolt_hand_position_cm']<.01 and metrics['bolt_hand_rotation_deg']<.1,metrics
        assert metrics['extraction_contact_cm']<.03 and metrics['extraction_contact_deg']<.15,metrics
        assert metrics['bone_length_delta_cm']<.01 and metrics['outside_window_left_local_error']<1e-4,metrics
        assert metrics['empty_support_position_cm']<.02,metrics
        if family=='base':
            frames=(19.75,21,22,24,25.25) if role=='reload' else (55,62,68,77,87,98,110)
            for f in frames:view(local_pose(clip,new,f/30)[0],folder/(role+'_'+str(f)+'.png'))
# Match the exact runtime C++ Hermite clock, inverted only for reporting.
source=[0,8,18,21,24,27,29,30,34,38,40,44,50,54]
paced=[0,8,24,34,43,54,60.666667,79,92,105,111,119,131,135]
def source_at_runtime_frames(f):
    if f>=paced[-1]:return f-81
    i=next(i for i in range(len(paced)-1) if f<=paced[i+1]);span=paced[i+1]-paced[i];w=(f-paced[i])/span
    def slope(k):
        if k==0 or k==len(source)-1:return 1.
        a=(source[k]-source[k-1])/(paced[k]-paced[k-1]);b=(source[k+1]-source[k])/(paced[k+1]-paced[k]);return 2*a*b/(a+b)
    return (2*w**3-3*w*w+1)*source[i]+(w**3-2*w*w+w)*span*slope(i)+(-2*w**3+3*w*w)*source[i+1]+(w**3-w*w)*span*slope(i+1)
def bisect_target(fn,value,hi=140.):
    lo=0.
    for _ in range(48):
        mid=(lo+hi)/2
        if fn(mid)<value:lo=mid
        else:hi=mid
    return (lo+hi)/2
old_start=bisect_target(source_at_runtime_frames,19)/30;old_end=bisect_target(source_at_runtime_frames,22)/30
new_start=bisect_target(lambda f:source_frame(source_at_runtime_frames(f)),19)/30;new_end=bisect_target(lambda f:source_frame(source_at_runtime_frames(f)),22)/30
report['pacing']={'old_straight_pull_s':old_end-old_start,'new_straight_pull_s':new_end-new_start,'out_contact_source_frame':source_frame(21),'release_source_frame':source_frame(25.25),'new_magazine_gap_extra_s':.5,'normal_total_s':4.7,'empty_total_s':191/30,'minimum_remap_step':min(source_frame(18+(i+1)/100)-source_frame(18+i/100) for i in range(725)),'runtime_tested':False}
assert report['pacing']['minimum_remap_step']>0
(O/'review.json').write_text(json.dumps(report,indent=2));print('M24_RELOAD_REVIEW',json.dumps(report),flush=True)
