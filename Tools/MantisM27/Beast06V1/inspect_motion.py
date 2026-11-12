"""Requested source/candidate and pounce boundary inspection, offline only."""
from pathlib import Path
import json,math
import bpy
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27'); OUT=BASE/'Beast06V1'
def deg(a,b):return math.degrees(2*math.acos(min(1.,abs(a.dot(b)))))
def capture(revision,roles):
    bpy.ops.wm.open_mainfile(filepath=str(BASE/revision/'Delivery'/('MantisM27_'+revision+'.blend')))
    scene=bpy.context.scene; rig=next(o for o in scene.objects if o.type=='ARMATURE')
    for tr in rig.animation_data.nla_tracks: tr.mute=True
    clips={}; reports={}
    for role,count in roles:
        rig.animation_data.action=bpy.data.actions['A_M27_'+role+'_'+revision]
        if rig.animation_data.action.slots: rig.animation_data.action_slot=rig.animation_data.action.slots[0]
        frames=[]
        for i in range(count):
            scene.frame_set(i+1); frames.append({b.name:b.matrix.copy() for b in rig.pose.bones})
        reports[role]={}
        for n in ['pelvis','spine_03','head','blade_root_l','blade_root_r']:
            maximum=max((deg(frames[i][n].to_quaternion(),frames[i-1][n].to_quaternion()),i/60) for i in range(1,count))
            reports[role][n]={'maximum_step_degrees':maximum[0],'time_seconds':maximum[1]}
        clips[role]=frames
    return clips,reports
accepted,accepted_report=capture('ClawV14',[('LeftSlash',40),('RightSlash',40)])
candidate,candidate_report=capture('Beast06V1',[('LeftSlash',40),('RightSlash',40),('HitF',49),('HitB',49),('HitL',49),('HitR',49),('Idle',401)])
pounce,pounce_report=capture('PounceV11',[('PounceWindup',37),('PounceFlight',40),('PounceLand',49)])
boundaries={}
for a,b in [('PounceWindup','PounceFlight'),('PounceFlight','PounceLand')]:
    first,last=pounce[a][-1],pounce[b][0]
    boundaries[a+' -> '+b]={n:{'position_cm':(first[n].translation-last[n].translation).length,
        'rotation_deg':deg(first[n].to_quaternion(),last[n].to_quaternion())}
        for n in ['pelvis','head','foot_l','foot_r','blade_root_l','blade_root_r','blade_tip_l','blade_tip_r']}
report={'accepted_claw_v14':accepted_report,'candidates':candidate_report,'pounce_v11':pounce_report,
        'pounce_boundaries':boundaries,'scope':'Offline source poses in component space; no collision, network or game acceptance'}
(OUT/'motion_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M27_BEAST06_MOTION_INSPECTION_SAVED',flush=True)
