"""Read the linked RTM for a scoped motion study; no game assets are changed.

RTM_0101 stores deformation matrices, not standalone joint transforms.
Rotational changes are measured here; joint paths require the source bind rig.
Format: https://community.bistudio.com/wiki/RTM
"""
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

root = Path(__file__).parent
data = (root / 'm1014_Reload.rtm').read_bytes()
offset = 0

def take(fmt):
    global offset
    value = struct.unpack_from('<' + fmt, data, offset)
    offset += struct.calcsize('<' + fmt)
    return value

def name():
    return take('32s')[0].split(b'\0', 1)[0].decode('ascii')

magic = take('8s')[0].decode('ascii')
if magic != 'RTM_0101':
    raise ValueError('Expected the plain RTM_0101 format')
motion = take('3f')
frame_count, bone_count = take('2I')
bones = [name() for _ in range(bone_count)]
frames = []
for index in range(frame_count):
    phase = take('f')[0]
    transforms = {}
    for bone in bones:
        record_name = name()
        if record_name != bone:
            raise ValueError('Bone order differs from the RTM header')
        transforms[bone] = take('12f')
    frames.append({'phase': phase, 'deformation': transforms})
if offset != len(data):
    raise ValueError('Unexpected trailing RTM data')

def matrix(values):
    # Convert source XZY row-vector deformation to Blender XYZ column-vector.
    a = np.eye(4)
    a[:3, :3] = np.array(values[:9]).reshape(3, 3).T
    a[:3, 3] = values[9:12]
    swap = np.eye(4)[[0, 2, 1, 3]]
    return swap @ a @ swap

def excursion(rotations):
    relative = rotations * rotations[0].inv()
    angles = np.rad2deg(relative.magnitude())
    peak = int(np.argmax(angles))
    steps = np.rad2deg((rotations[1:] * rotations[:-1].inv()).magnitude())
    return {'peak_change_from_first_deg': float(angles[peak]),
            'peak_phase': frames[peak]['phase'],
            'max_adjacent_key_rotation_deg': float(steps.max())}

matrices = {bone: np.array([matrix(f['deformation'][bone]) for f in frames]) for bone in bones}
rotations = {bone: Rotation.from_matrix(values[:, :3, :3]) for bone, values in matrices.items()}
summary = {
    'source': 'https://github.com/HopeJohnson/AAnim/blob/50d731135a81977d0ed758872a35b2185dcae296/Anim/reloadactions/m1014_Reload.rtm',
    'sha256': hashlib.sha256(data).hexdigest(),
    'format': magic, 'bytes': len(data), 'frames': frame_count, 'bones': bone_count,
    'motion_vector': motion, 'phase_range': [frames[0]['phase'], frames[-1]['phase']],
    'bone_names': bones, 'rotational_excursions': {}, 'relative_rotational_excursions': {},
    'limitations': ['No source bind rig or mesh in this RTM.',
                   'No absolute seconds or frame rate encoded; timing comes from the animation config.',
                   'These are deformation transforms; their translation is not the hand joint position.',
                   'No rendered or in-game assessment performed.']
}
for bone in bones:
    if any(token in bone.lower() for token in ('shoulder', 'arm', 'hand', 'weapon', 'magazine', 'camera')):
        summary['rotational_excursions'][bone] = excursion(rotations[bone])
lookup = {n.lower(): n for n in bones}
for parent, child in [('weapon', 'righthand'), ('weapon', 'lefthand'),
                      ('leftforearm', 'lefthand'), ('rightforearm', 'righthand')]:
    if parent in lookup and child in lookup:
        relation = rotations[lookup[parent]].inv() * rotations[lookup[child]]
        summary['relative_rotational_excursions'][parent + '->' + child] = excursion(relation)
(root / 'rtm_metadata.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
(root / 'rtm_frames.json').write_text(json.dumps({'bones': bones, 'frames': frames}, separators=(',', ':')), encoding='utf-8')
print(json.dumps({k: summary[k] for k in ('format', 'bytes', 'frames', 'bones', 'phase_range', 'bone_names', 'relative_rotational_excursions')}, indent=2))
