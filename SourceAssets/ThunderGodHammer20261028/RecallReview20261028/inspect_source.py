import bpy,json,math,os
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
throw=os.environ.get('THUNDER_REVIEW_KIND')=='throw'
prefix=(os.environ.get('THUNDER_REVIEW_PHASE','before')+'-throw-') if throw else ''
bpy.ops.wm.open_mainfile(filepath=str(P.parent/('ThunderThrowV1/ThunderHammer_Throw_Editable.blend' if throw else 'RecallCatchV2/ThunderHammer_RecallCatch_Editable.blend')))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
info={'objects':[{'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,
                 'materials':[m.name if m else None for m in o.data.materials] if o.type=='MESH' else [],
                 'vertices':len(o.data.vertices) if o.type=='MESH' else 0} for o in scene.objects],
      'actions':[{'name':a.name,'range':list(a.frame_range)} for a in bpy.data.actions]}
names=['WPN_root','upperarm_r','lowerarm_r','hand_r','upperarm_l','lowerarm_l','hand_l']
metrics={};poses={}
for clip,duration in ([('A_ThunderHammer_ThrowCharge',2.),('A_ThunderHammer_ThrowRelease',.86)] if throw else [('A_ThunderHammer_RecallReady_V2',.32),('A_ThunderHammer_Catch_V2',.60)]):
    a=bpy.data.actions[clip];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    prev=None;worst={n:{'distance_cm':0,'angle_degrees':0,'time':0} for n in names};local_worst={}
    samples=[]
    for i in range(round(duration*240)+1):
        scene.frame_set(i);now={n:rig.pose.bones[n].matrix.copy() for n in names}
        locals_={b.name:b.matrix_basis.to_quaternion() for b in rig.pose.bones}
        if prev:
            for n in names:
                dist=(now[n].translation-prev[n].translation).length*100
                ang=math.degrees(now[n].to_quaternion().rotation_difference(prev[n].to_quaternion()).angle);ang=min(ang,360-ang)
                if dist>worst[n]['distance_cm']:worst[n]['distance_cm']=dist;worst[n]['time']=i/240
                worst[n]['angle_degrees']=max(worst[n]['angle_degrees'],ang)
            for n,q in locals_.items():
                angle=math.degrees(q.rotation_difference(previous_locals[n]).angle);angle=min(angle,360-angle)
                if angle>local_worst.get(n,{}).get('degrees',0):local_worst[n]={'degrees':angle,'time':i/240}
        samples.append({n:[list(row) for row in m] for n,m in now.items()})
        prev=now;previous_locals=locals_
    metrics[clip]={'world_steps':worst,'largest_local_steps':sorted(local_worst.items(),key=lambda p:p[1]['degrees'],reverse=True)[:12]}
    poses[clip]=samples
info['metrics']=metrics
(P/(prefix+'source-inspection.json')).write_text(json.dumps(info,indent=2),encoding='utf-8')
(P/(prefix+'source-poses.json')).write_text(json.dumps(poses),encoding='utf-8')
print(json.dumps(info,indent=2))
