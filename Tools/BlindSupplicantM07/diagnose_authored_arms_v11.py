"""Finish the user's requested hand/arm source inspection after local repair.

Only numerical hand skin and arm joint/channel data are read. No rendering,
cloth playback, UE, PIE or general regression test is performed.
"""
import json
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT=ROOT/'RecoveryHandsV11'
manifest=json.loads((OUT/'rig_motion/motion_manifest_v11.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'M07_Original_HandArm_Master_V11.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
def qangle(q):return math.degrees(2*math.acos(min(1.,abs(q.normalized().w))))
report={'scope':'User-requested hand/arm model and bind inspection after repair',
        'runtime_tested':False,'rendered':False,'reference':{},'clips':{},'hand_skin':{}}
for side in ('l','r'):
    name='upperarm_'+side
    y=rest[name].to_3x3()@Vector((0,1,0))
    d=rest['lowerarm_'+side].translation-rest[name].translation
    report['reference'][side]={'upperarm_axis_error_deg':math.degrees(y.angle(d)),
        'upperarm_tail_to_elbow_cm':(rig.data.bones[name].tail_local-rest['lowerarm_'+side].translation).length}
rig.data.pose_position='POSE'
for role,entry in manifest['clips'].items():
    action=bpy.data.actions[entry['action']]
    rig.animation_data_create();rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    max_wrist=max_location=max_plane=0.
    previous={}
    for frame in range(1,entry['frames']+1):
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        torso=rig.pose.bones['spine_03'].matrix.to_quaternion()@rest['spine_03'].to_quaternion().inverted()
        for side in ('l','r'):
            matrices={n:rig.pose.bones[n+'_'+side].matrix.copy() for n in ('upperarm','lowerarm','hand')}
            neutral=matrices['lowerarm'].to_quaternion()@rest['lowerarm_'+side].to_quaternion().inverted()@rest['hand_'+side].to_quaternion()
            max_wrist=max(max_wrist,qangle(neutral.inverted()@matrices['hand'].to_quaternion()))
            a,b,c=[matrices[n].translation for n in ('upperarm','lowerarm','hand')]
            plane=(b-a).cross(c-b).normalized()
            local=torso.inverted()@plane
            if side in previous:max_plane=max(max_plane,math.degrees(local.angle(previous[side])))
            previous[side]=local
        for p in rig.pose.bones:
            if p.name.startswith(('upperarm_','lowerarm_','hand_','thumb_','index_','middle_','ring_','pinky_')):
                max_location=max(max_location,p.location.length)
    report['clips'][role]={'max_residual_wrist_deg':max_wrist,
        'max_arm_child_location_cm':max_location,'max_elbow_plane_step_torso_deg':max_plane}
names=[b.name for b in rig.data.bones];lookup={n:i for i,n in enumerate(names)}
for name in ('M07_OriginalBody_High','M07_OriginalBody_Display'):
    obj=bpy.data.objects[name];p=np.empty((len(obj.data.vertices),3),np.float32)
    obj.data.vertices.foreach_get('co',p.ravel())
    edges=np.empty((len(obj.data.edges),2),np.int32);obj.data.edges.foreach_get('vertices',edges.ravel())
    selected=(np.abs(p[:,0])>118.)&(p[:,2]>224.)
    edges=edges[selected[edges].all(axis=1)]
    field=np.zeros((len(p),len(names)),np.float32)
    group={g.index:lookup[g.name] for g in obj.vertex_groups if g.name in lookup}
    for v in obj.data.vertices:
        if not selected[v.index]:continue
        for g in v.groups:
            if g.group in group:field[v.index,group[g.group]]=g.weight
    length=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)
    difference=np.abs(field[edges[:,0]]-field[edges[:,1]]).sum(axis=1)
    short=length<1.
    report['hand_skin'][name]={'short_edges_with_weight_l1_over_1':int((short&(difference>1.)).sum()),
        'max_l1_per_cm':float((difference/np.maximum(length,.001)).max(initial=0.)),
        'max_short_edge_weight_l1':float(difference[short].max(initial=0.))}
destination=OUT/'diagnosis/authored_hand_arm_findings_v11.json'
destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M07_REQUESTED_AUTHORED_ARM_INSPECTION '+json.dumps(report),flush=True)
