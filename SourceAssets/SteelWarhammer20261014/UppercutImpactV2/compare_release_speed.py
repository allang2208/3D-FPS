"""Requested comparison of actual sword/hammer poses under their playback clocks.

No pose is edited: the same saved hammer take is sampled before/after retiming.
The measured interval is main release through arrest, excluding recovery.
"""
import bpy,json,math,re,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
shared=R/'Source/FPSGAME/Weapons/RuneSwordUppercutMotion.h'
special=R/'Source/FPSGAME/Production/WarhammerUppercutMotion.h'
h=shared.read_text('utf-8');hammer_header=special.read_text('utf-8')
number=lambda name:float(re.search(r'\b'+name+r'\s*=\s*([.\d]+)f?\s*;',h)[1])
FPS=number('SampleRate');release=number('ReleaseFrame')/FPS;stroke_end=number('StrokeEndFrame')/FPS
finish=number('FinishFrame')/FPS;stride_seconds=number('SkillLungeSeconds');stride_source=release+6/FPS
stride_end=release+stride_seconds;extra=stride_seconds-(stride_source-release)
strike_start=stride_end-.075;loaded_source=release+.008
def sword_time(t):
    if t<=release:return t
    if t<stride_end:return release+(t-release)*(stride_source-release)/stride_seconds
    return t-extra
def hermite(t,a,b,first,last,va,vb):
    d=b-a;u=max(0.,min(1.,(t-a)/d))
    return (2*u**3-3*u*u+1)*first+(u**3-2*u*u+u)*d*va+(-2*u**3+3*u*u)*last+(u**3-u*u)*d*vb
def hammer_time(t):
    if t<=release:return t
    if t<strike_start:return hermite(t,release,strike_start,release,loaded_source,0.,.1)
    if t<stride_end:return hermite(t,strike_start,stride_end,loaded_source,stride_source,.1,1.)
    return sword_time(t)
def angle(a,b):
    q=a.rotation_difference(b);return math.degrees(2*math.atan2(math.sqrt(q.x*q.x+q.y*q.y+q.z*q.z),abs(q.w)))
results={};HZ=600;start=release;end=finish+extra
for label,path,action,clock in (
    ('sword_current',R/'SourceAssets/SwordUppercut20261003/GripRecoveryV15/Standard/Sword_UppercutV15_Editable.blend','Sword_UppercutV15_Standard',sword_time),
    ('hammer_before',P.parent/'UppercutV1/Warhammer_Uppercut_Editable.blend','A_Warhammer_Uppercut',sword_time),
    ('hammer_after',P.parent/'UppercutV1/Warhammer_Uppercut_Editable.blend','A_Warhammer_Uppercut',hammer_time)):
    bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene
    rig=next(o for o in s.objects if o.type=='ARMATURE');a=bpy.data.actions[action]
    rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    rates=[];total=0.;last=None
    for i in range(round((end-start)*HZ)+1):
        t=start+i/HZ;source=clock(t);f=source*s.render.fps;s.frame_set(int(f),subframe=f-int(f))
        q=rig.pose.bones['WPN_root'].matrix.to_quaternion()
        if last is not None:
            delta=angle(last,q);total+=delta;rates.append({'time':t,'degrees_per_second':delta*HZ,'total_degrees':total})
        last=q
    def percentile(frac):return next(x['time'] for x in rates if x['total_degrees']>=total*frac)
    peak=max(rates,key=lambda x:x['degrees_per_second'])
    results[label]={'source':str(path),'angular_travel_degrees':total,'travel_10_seconds':percentile(.1),'travel_90_seconds':percentile(.9),
        'main_travel_10_to_90_seconds':percentile(.9)-percentile(.1),'peak_degrees_per_second':peak['degrees_per_second'],
        'peak_at_seconds':peak['time'],'samples':rates}
report={'header_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (shared,special)},
    'clock_contract':{'windup_seconds':release,'stride_start':release,'stride_end':stride_end,'burst_start':strike_start,
        'main_stroke_end':stroke_end+extra,'contact_end':finish+extra,'total_seconds':number('EndFrame')/FPS+extra},
    'source_assets_changed':False,'runtime_tested':False,'comparisons':results}
monotonic=all(hammer_time((i+1)/HZ)>=hammer_time(i/HZ)-1e-8 for i in range(round(2.28*HZ)))
report['monotonic_source_clock']=monotonic
report['same_forward_crossing_source_time']=abs(hammer_time(stride_end)-sword_time(stride_end))<1e-8
report['main_travel_speed_ratio']=results['hammer_before']['main_travel_10_to_90_seconds']/results['hammer_after']['main_travel_10_to_90_seconds']
(P/'release_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:{a:b for a,b in v.items() if a!='samples'} for k,v in results.items()}),flush=True)
if not monotonic or not report['same_forward_crossing_source_time']:raise RuntimeError('Timing contract is discontinuous')
