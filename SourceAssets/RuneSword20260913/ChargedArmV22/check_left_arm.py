"""Focused retained-bone, elbow continuity and charge-seam comparison."""
import bpy,json,math,sys
from pathlib import Path

P=Path(__file__).parent
sys.path.insert(0,str(P.parent/'CompactRecoveryV8'))
from rhythm_clock import source_time
changed={'clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l'}
sources={};seams={}

def angle(a,b):
    q=a.to_quaternion().rotation_difference(b.to_quaternion())
    return math.degrees(2*math.atan2(math.sqrt(q.x*q.x+q.y*q.y+q.z*q.z),abs(q.w)))

for version in ('FistBraceGuardV21','ChargedArmV22'):
    bpy.ops.wm.open_mainfile(filepath=str(P.parent/version/'AzureRunesword_Manny_Editable.blend'))
    r=bpy.data.objects['SK_RuneSword_Rig'];s=bpy.context.scene
    def sample(clip,t):
        a=bpy.data.actions['A_RuneSword_'+clip]
        r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
        f=t*480;s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
        return {b.name:b.matrix.copy() for b in r.pose.bones}
    records={}
    for clip in ('HeavyCharge','HeavyRelease','Slash1'):
        a=bpy.data.actions['A_RuneSword_'+clip];start,end=map(int,a.frame_range)
        records[clip]=[sample(clip,k/960) for k in range(start*2,end*2+1)]
    sources[version]=records
    entries=[]
    pairs=[('full_charge','HeavyCharge',2.,'HeavyRelease',0.),
           ('release_idle_endpoint','HeavyRelease',1.,'HeavyCharge',0.),
           ('slash_idle_endpoint','Slash1',1.775,'HeavyCharge',0.)]
    for t in (.03,.07,.12,.2,.4,.65,1.,1.4,1.6,1.9):
        target=.17*t/.65 if t<.65 else .17+.23*max(0.,min(1.,(t-.65)/.95))
        lo,hi=0.,.65
        for _ in range(16):
            mid=(lo+hi)/2
            if source_time(mid)<target:lo=mid
            else:hi=mid
        pairs.append(('short_charge_'+str(t),'HeavyCharge',t,'Slash1',(lo+hi)/2))
    for name,ac,at,bc,bt in pairs:
        a,b=sample(ac,at),sample(bc,bt)
        entries.append({'name':name,'left_upper_angle_deg':angle(a['upperarm_l'],b['upperarm_l']),
                        'left_upper_position_mm':(a['upperarm_l'].translation-b['upperarm_l'].translation).length*1000,
                        'left_hand_position_mm':(a['hand_l'].translation-b['hand_l'].translation).length*1000})
    seams[version]=entries

report=[]
for clip,before in sources['FistBraceGuardV21'].items():
    after=sources['ChargedArmV22'][clip]
    max_position=max_rotation=max_length=0.;steps=[];worst_position={}
    key_position=key_rotation=right_position=0.
    for i,(a,b) in enumerate(zip(before,after)):
        for n in a:
            if n in changed:continue
            position=(a[n].translation-b[n].translation).length*1000
            rotation=angle(a[n],b[n])
            if position>max_position:worst_position={'bone':n,'seconds':i/960}
            max_position=max(max_position,position);max_rotation=max(max_rotation,rotation)
            if i%2==0:key_position=max(key_position,position);key_rotation=max(key_rotation,rotation)
            if n in ('hand_r','WPN_root','Blade_Tip'):right_position=max(right_position,position)
        for root,tip in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]:
            al=(a[tip].translation-a[root].translation).length
            bl=(b[tip].translation-b[root].translation).length
            max_length=max(max_length,abs(al-bl)*1000)
        if i:steps.append({'time':i/960,'before_deg':angle(before[i-1]['upperarm_l'],a['upperarm_l']),
                           'after_deg':angle(after[i-1]['upperarm_l'],b['upperarm_l'])})
    report.append({'clip':clip,'samples_at_960_hz':len(after),'frame_count_unchanged':len(before)==len(after),
        'max_retained_bone_position_delta_mm':max_position,'max_retained_rotation_delta_deg':max_rotation,
        'max_arm_segment_length_delta_mm':max_length,
        'worst_position_sample':worst_position,'max_retained_key_position_delta_mm':key_position,
        'max_retained_key_rotation_delta_deg':key_rotation,'max_right_hand_weapon_delta_mm':right_position,
        'largest_steps':sorted(steps,key=lambda x:x['after_deg'],reverse=True)[:5],
        'largest_original_step_deg':max(x['before_deg'] for x in steps)})
result={'preservation':report,'seams':seams}
(P/'source_preservation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2),flush=True)
