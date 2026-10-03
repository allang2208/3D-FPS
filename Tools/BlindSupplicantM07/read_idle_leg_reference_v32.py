"""Read the requested idle anatomy and existing melee support for authoring."""
import json
import math
import sys
from pathlib import Path
import bpy
sys.path.insert(0, str(Path(__file__).parent))
import author_library_sweep_v27 as base

manifest = json.loads((base.ROOT/'SupportHoverV30/Motion/support_hover_manifest_v30.json').read_text())
bpy.ops.wm.open_mainfile(filepath=manifest['source'])
rig = base.v20.original_rig()
rig.data.pose_position = 'POSE'
ordered = sorted(rig.pose.bones, key=lambda p:len(p.bone.parent_recursive))
idle = base.v17.cache_action(rig, bpy.data.actions['A_M07_Idle_PalmArmV20'], 1, ordered)[0]
for label, pose in [('idle',idle), ('rest',{b.name:b.matrix_local.copy() for b in rig.data.bones})]:
    for side in ('l','r'):
        h,k,a = [pose[n+'_'+side].translation for n in ('thigh','calf','foot')]
        upper,lower = (k-h).normalized(),(a-k).normalized()
        print('V32_REFERENCE',label,side,json.dumps(dict(hip=list(h),knee=list(k),ankle=list(a),
            upper=list(upper),lower=list(lower),hinge=list(upper.cross(lower).normalized()),
            flexion=math.degrees(upper.angle(lower)),thigh_q=list(pose['thigh_'+side].to_quaternion()),
            calf_q=list(pose['calf_'+side].to_quaternion()))),flush=True)
for role in ('SweepLeft','SweepRight'):
    entry = manifest['clips'][role]
    poses = base.v17.cache_action(rig,bpy.data.actions[entry['action']],entry['frames'],ordered)
    for i in (0,18,36,60,90,120):
        p = poses[i]
        print('V32_SUPPORT',role,i,json.dumps({n:list(p[n].translation) for n in ('pelvis','thigh_l','thigh_r','foot_l','foot_r')}),flush=True)
