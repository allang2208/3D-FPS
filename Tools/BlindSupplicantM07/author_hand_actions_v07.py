"""Author local anatomical finger motion after the common body adaptation."""
import json
import math
from pathlib import Path

from mathutils import Quaternion, Vector

SOURCE = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV07/hands')


def apply_motion(rig, action, role, frames, fps, activate):
    guides = json.loads((SOURCE/'hand_action_guides_v07.json').read_text(encoding='utf-8'))
    poses = guides['recommended_curl_degrees']

    def smooth(x):
        x = max(0., min(1., x))
        return x*x*(3.-2.*x)

    activate(rig, action)
    for frame in range(1, frames+1):
        u = (frame-1)/max(1, frames-1)
        if role in ('SlowWalk', 'Chase'):
            target, strength = 'Locomotion', 1.
        elif role.startswith('Melee'):
            contact = .68/1.5 if role == 'MeleeLeft' else .78/(50/30)
            target = 'Attack'
            strength = smooth(u/max(.01, contact))*(1.-smooth((u-contact)/max(.01, 1-contact)))
        elif role == 'Hit':
            target, strength = 'HitOpen', math.sin(math.pi*u)**2
        elif role in ('Death', 'Fall'):
            target, strength = 'DeathRelax', smooth(u/.6)
        else:
            target, strength = 'Idle', 1.
        for side in ('l', 'r'):
            phase = 0. if side == 'l' else math.pi
            for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                # Palm-support helpers do not duplicate thumb CMC flexion.
                meta = rig.pose.bones[finger+'_metacarpal_'+side]
                meta.rotation_quaternion = Quaternion()
                meta.keyframe_insert(data_path='rotation_quaternion', frame=frame)
                for i in range(3):
                    angle = poses['Idle'][finger][i]*(1-strength)+poses[target][finger][i]*strength
                    if role in ('SlowWalk', 'Chase'):
                        angle += 1.3*math.sin(2*math.pi*u+phase+i*.3)
                    pb = rig.pose.bones[f'{finger}_{i+1:02d}_{side}']
                    pb.rotation_mode = 'QUATERNION'
                    curl = Quaternion(Vector((1., 0., 0.)), math.radians(angle))
                    if finger == 'thumb' and i == 0:
                        opposition = 3.+(5.*strength if target == 'Attack' else 0.)
                        curl = curl @ Quaternion(Vector((0., 1., 0.)), math.radians(opposition))
                    pb.rotation_quaternion = curl
                    pb.keyframe_insert(data_path='rotation_quaternion', frame=frame)
    action['hand_motion_source'] = str(SOURCE/'hand_action_guides_v07.json')
    action['thumb_01_semantics'] = 'CMC metacarpal; thumb_02 MCP proximal; thumb_03 IP distal'
